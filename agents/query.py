"""Agente de consulta: transforma a pergunta do aluno em uma consulta SQL."""

import re

from exceptions import SaidaDoAgenteInvalidaError
from llm import (
    ERRO_ANTERIOR,
    INTENCAO,
    PERGUNTA,
    SCHEMA,
    SQL_ANTERIOR,
    LLMClient,
    build_blocks,
)
from models import Intent

SYSTEM_PROMPT = (
    "Você é o agente de consulta de um assistente de álgebra para estudantes. "
    "Escreva UMA única consulta SQLite que responda à PERGUNTA do aluno, "
    "considerando a INTENCAO e usando somente as tabelas e colunas descritas em SCHEMA. "
    "Regras: a consulta deve ser somente de leitura (SELECT), deve conter LIMIT "
    "e não pode ter ponto e vírgula no meio. "
    "Se houver SQL_ANTERIOR e ERRO_ANTERIOR, corrija o SQL anterior de modo a "
    "resolver o erro informado. "
    "Responda SOMENTE com o SQL, sem explicações e sem cercas de código."
)

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*[ \t]*\n?(.*?)\n?```$", re.DOTALL)
_SELECT_RE = re.compile(r"\bselect\b", re.IGNORECASE)


def _strip_fences(texto: str) -> str:
    texto = texto.strip()
    achado = _FENCE_RE.match(texto)
    return achado.group(1).strip() if achado else texto


class QueryAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def generate_sql(
        self,
        pergunta: str,
        intent: Intent,
        schema: str,
        sql_anterior: str | None = None,
        erro_anterior: str | None = None,
    ) -> str:
        blocos = {PERGUNTA: pergunta, INTENCAO: intent.value, SCHEMA: schema}
        if sql_anterior is not None and erro_anterior is not None:
            blocos[SQL_ANTERIOR] = sql_anterior
            blocos[ERRO_ANTERIOR] = erro_anterior

        bruto = self._llm.complete(SYSTEM_PROMPT, build_blocks(**blocos))
        sql = _strip_fences(bruto)
        if not sql or not _SELECT_RE.search(sql):
            raise SaidaDoAgenteInvalidaError(
                "O agente de consulta não devolveu uma consulta SQL válida."
            )
        return sql
