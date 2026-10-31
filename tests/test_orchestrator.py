import pytest

from agents.formatter import FormatterAgent
from agents.query import QueryAgent
from agents.router import RouterAgent
from database import Database
from llm import MockLLMClient
from models import Intent
from orchestrator import Orchestrator, build_orchestrator
from tests.fakes import FakeLLMClient

SQL_RUIM = "SELECT * FROM Exercicios"
SQL_BOM = "SELECT t.nome, e.enunciado_latex, e.dificuldade FROM Exercicios e JOIN Topicos_Algebra t ON t.id = e.topico_id LIMIT 5"
SQL_SEM_LINHAS = "SELECT t.nome FROM Topicos_Algebra t WHERE t.nome LIKE '%inexistente%' LIMIT 5"


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "edu.db")
    database.ensure_ready()
    return database


def make(db, router=None, query=None, formatter=None, **kwargs) -> Orchestrator:
    mock = MockLLMClient()
    return Orchestrator(
        RouterAgent(router or mock),
        QueryAgent(query or mock),
        FormatterAgent(formatter or mock),
        db,
        **kwargs,
    )


def test_fluxo_feliz(db):
    r = make(db).handle("exercícios de equação do 2º grau")
    assert r.status == "ok"
    enunciados = [x["enunciado_latex"] for x in db.execute_readonly(
        "SELECT e.enunciado_latex FROM Exercicios e JOIN Topicos_Algebra t "
        "ON t.id = e.topico_id WHERE t.nome LIKE '%2º Grau%' LIMIT 5")]
    assert any(e in r.text for e in enunciados)
    assert r.trace.intent == Intent.BUSCAR_EXERCICIOS
    assert len(r.trace.attempts) == 1
    assert r.trace.attempts[0].row_count > 0
    assert r.trace.attempts[0].error is None
    assert {"roteador", "consulta", "banco", "formatador"} <= set(r.trace.tempos_ms)


@pytest.mark.parametrize(
    "pergunta, intent, topico",
    [
        ("resumo de fatoração", Intent.BUSCAR_RESUMO, "Fatoração"),
        ("resolução de sistemas lineares", Intent.BUSCAR_RESOLUCAO, "Sistemas"),
    ],
)
def test_resumo_e_resolucao(db, pergunta, intent, topico):
    r = make(db).handle(pergunta)
    assert r.status == "ok"
    assert r.trace.intent == intent
    if intent is Intent.BUSCAR_RESUMO:
        coluna, sql = "resumo_teorico", "SELECT resumo_teorico AS c FROM Topicos_Algebra WHERE nome LIKE '%Fatoração%' LIMIT 1"
    else:
        coluna, sql = "passo_a_passo_latex", (
            "SELECT r.passo_a_passo_latex AS c FROM Resolucoes r JOIN Exercicios e ON e.id = r.exercicio_id "
            "JOIN Topicos_Algebra t ON t.id = e.topico_id WHERE t.nome LIKE '%Sistemas%' LIMIT 1")
    assert db.execute_readonly(sql)[0]["c"] in r.text


def test_fora_do_escopo(db):
    r = make(db).handle("qual a capital da França")
    assert r.status == "fora_do_escopo"
    assert r.trace.attempts == []
    assert r.trace.intent == Intent.FORA_DO_ESCOPO


def test_retry_com_gancho(db):
    r = make(db).handle("teste retry exercícios de fatoração")
    assert r.status == "ok"
    assert len(r.trace.attempts) == 2
    assert r.trace.attempts[0].error
    assert r.trace.attempts[0].sql == SQL_RUIM
    assert r.trace.attempts[1].error is None


def test_esgota_tentativas(db):
    query = FakeLLMClient([SQL_RUIM])
    r = make(db, query=query).handle("exercícios de fatoração")
    assert r.status == "erro"
    assert len(r.trace.attempts) == 3
    assert all(a.error for a in r.trace.attempts)
    assert len(query.calls) == 3
    # a partir da 2ª tentativa o agente recebe SQL e erro anteriores
    assert "SQL_ANTERIOR:" not in query.calls[0][1]
    assert "SQL_ANTERIOR:" in query.calls[1][1]
    assert "ERRO_ANTERIOR:" in query.calls[1][1]


def test_max_attempts_configuravel(db):
    r = make(db, query=FakeLLMClient([SQL_RUIM]), max_attempts=2).handle("exercícios de fatoração")
    assert r.status == "erro"
    assert len(r.trace.attempts) == 2


def test_saida_invalida_do_agente_conta_como_tentativa(db):
    query = FakeLLMClient(["Desculpe, não sei fazer isso.", SQL_BOM])
    r = make(db, query=query).handle("exercícios de fatoração")
    assert r.status == "ok"
    assert len(r.trace.attempts) == 2
    assert r.trace.attempts[0].sql == ""
    assert r.trace.attempts[0].error
    assert r.trace.attempts[1].error is None


def test_sem_resultados(db):
    formatter = FakeLLMClient(["não deveria ser chamado"])
    r = make(db, query=FakeLLMClient([SQL_SEM_LINHAS]), formatter=formatter).handle(
        "exercícios de fatoração"
    )
    assert r.status == "sem_resultados"
    assert formatter.calls == []
    assert len(r.trace.attempts) == 1
    assert r.trace.attempts[0].row_count == 0
    assert "formatador" not in r.trace.tempos_ms


def test_erro_nao_recuperavel(db):
    query = FakeLLMClient([SQL_BOM])
    r = make(db, router=FakeLLMClient(["isto não é JSON"]), query=query).handle(
        "exercícios de fatoração"
    )
    assert r.status == "erro"
    assert query.calls == []
    assert r.trace.attempts == []
    assert r.trace.avisos  # detalhe técnico fica no trace


class _BancoEspiao(Database):
    def __init__(self, path):
        super().__init__(path)
        self.calls = 0

    def execute_readonly(self, sql):
        self.calls += 1
        return super().execute_readonly(sql)


@pytest.mark.parametrize("texto", ["", "   \n"])
def test_entrada_vazia(tmp_path, texto):
    espiao = _BancoEspiao(tmp_path / "edu.db")
    espiao.ensure_ready()
    llms = [FakeLLMClient(["{}"]) for _ in range(3)]
    orq = Orchestrator(
        RouterAgent(llms[0]), QueryAgent(llms[1]), FormatterAgent(llms[2]), espiao
    )
    r = orq.handle(texto)
    assert r.status == "fora_do_escopo"
    assert all(llm.calls == [] for llm in llms)
    assert espiao.calls == 0


def test_latex_invalido_vira_aviso(db):
    r = make(db, formatter=FakeLLMClient(["$ x"])).handle("exercícios de fatoração")
    assert r.status == "ok"
    assert "```" in r.text
    assert len(r.trace.avisos) == 1
    assert "latex" in r.trace.tempos_ms


def test_build_orchestrator(tmp_path):
    caminho = tmp_path / "sub" / "edu.db"
    r = build_orchestrator(caminho).handle("exercícios de fatoração")
    assert caminho.exists()
    assert r.status == "ok"
