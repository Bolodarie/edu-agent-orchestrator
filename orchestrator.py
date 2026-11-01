"""Orquestrador: único ponto que enxerga agentes e banco juntos.

Coordena roteador -> consulta (com retry) -> banco -> formatador -> validação de
LaTeX. Camadas inferiores só levantam ``AgentPipelineError``; aqui elas são
capturadas e traduzidas em ``status``. Detalhes técnicos vão para o ``trace``;
o texto devolvido ao aluno vem das constantes abaixo.
"""

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from agents.formatter import FormatterAgent
from agents.query import QueryAgent
from agents.router import RouterAgent
from database import Database
from exceptions import AgentPipelineError
from latex_validator import validate_latex
from llm import MockLLMClient
from models import Intent, OrchestratorResponse, QueryAttempt, Status, Trace

# Ancorado no módulo (não no cwd): o app roda de qualquer diretório.
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "edu.db"

MSG_FORA_DO_ESCOPO = (
    "Só consigo ajudar com álgebra: exercícios, resumos teóricos e resoluções "
    "passo a passo. Tente, por exemplo, \"exercícios de equação do 2º grau\"."
)
MSG_SEM_RESULTADOS = (
    "Não encontrei nada sobre isso no meu banco de álgebra. "
    "Tente outro tópico, como fatoração, sistemas lineares ou equações do 1º e 2º grau."
)
MSG_ERRO = (
    "Desculpe, não consegui responder agora. "
    "Tente reformular a pergunta ou tente novamente em instantes."
)


class Orchestrator:
    def __init__(
        self,
        router: RouterAgent,
        query_agent: QueryAgent,
        formatter: FormatterAgent,
        database: Database,
        max_attempts: int = 3,
    ) -> None:
        self._router = router
        self._query_agent = query_agent
        self._formatter = formatter
        self._database = database
        self._max_attempts = max_attempts

    def handle(self, texto: str) -> OrchestratorResponse:
        trace = Trace()
        pergunta = texto.strip()
        if not pergunta:
            return _resposta(MSG_FORA_DO_ESCOPO, "fora_do_escopo", trace)
        try:
            return self._run(pergunta, trace)
        except AgentPipelineError as exc:
            trace.avisos.append(f"{type(exc).__name__}: {exc}")
            return _resposta(MSG_ERRO, "erro", trace)
        except Exception as exc:  # último recurso: nada escapa de handle()
            # Detalhe técnico só no trace; o aluno vê apenas MSG_ERRO.
            trace.avisos.append(f"{type(exc).__name__}: {exc}")
            return _resposta(MSG_ERRO, "erro", trace)

    def _run(self, pergunta: str, trace: Trace) -> OrchestratorResponse:
        with _medir(trace, "roteador"):
            rota = self._router.classify(pergunta)
        trace.intent, trace.confidence = rota.intent, rota.confidence
        if rota.intent is Intent.FORA_DO_ESCOPO:
            return _resposta(MSG_FORA_DO_ESCOPO, "fora_do_escopo", trace)

        rows = self._consultar(pergunta, rota.intent, trace)
        if rows is None:
            return _resposta(MSG_ERRO, "erro", trace)
        if not rows:
            return _resposta(MSG_SEM_RESULTADOS, "sem_resultados", trace)

        with _medir(trace, "formatador"):
            bruto = self._formatter.format(rota.intent, rows)
        with _medir(trace, "latex"):
            texto, avisos = validate_latex(bruto)
        trace.avisos.extend(avisos)
        return _resposta(texto, "ok", trace)

    def _consultar(
        self, pergunta: str, intent: Intent, trace: Trace
    ) -> list[dict] | None:
        """Gera e executa o SQL, com até ``max_attempts`` tentativas.

        Devolve as linhas, ou ``None`` se as tentativas se esgotaram. Erros não
        recuperáveis propagam (já registrados em ``trace.attempts``).
        """
        sql_anterior: str | None = None
        erro_anterior: str | None = None
        for _ in range(self._max_attempts):
            sql = ""
            try:
                with _medir(trace, "consulta"):
                    sql = self._query_agent.generate_sql(
                        pergunta,
                        intent,
                        self._database.schema_description,
                        sql_anterior,
                        erro_anterior,
                    )
                with _medir(trace, "banco"):
                    rows = self._database.execute_readonly(sql)
            except AgentPipelineError as exc:
                trace.attempts.append(QueryAttempt(sql=sql, error=str(exc)))
                if not exc.recuperavel:
                    raise
                sql_anterior, erro_anterior = sql, str(exc)
                continue
            trace.attempts.append(QueryAttempt(sql=sql, row_count=len(rows)))
            return rows
        return None


def build_orchestrator(db_path: str | Path = DEFAULT_DB_PATH) -> Orchestrator:
    llm = MockLLMClient()
    database = Database(db_path)
    database.ensure_ready()
    return Orchestrator(
        RouterAgent(llm), QueryAgent(llm), FormatterAgent(llm), database
    )


def _resposta(text: str, status: Status, trace: Trace) -> OrchestratorResponse:
    return OrchestratorResponse(text=text, status=status, trace=trace)


@contextmanager
def _medir(trace: Trace, chave: str) -> Iterator[None]:
    """Soma em ``trace.tempos_ms[chave]`` o tempo gasto no bloco (em ms)."""
    inicio = time.perf_counter()
    try:
        yield
    finally:
        decorrido = (time.perf_counter() - inicio) * 1000
        trace.tempos_ms[chave] = trace.tempos_ms.get(chave, 0.0) + decorrido
