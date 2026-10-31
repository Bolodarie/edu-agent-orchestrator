"""Agente formatador: transforma as linhas reais do banco em Markdown com LaTeX."""

import json
from typing import Any

from llm import LLMClient, build_blocks
from models import Intent

SYSTEM_PROMPT = (
    "Você é o formatador de um assistente de álgebra para estudantes. "
    "Receba a INTENCAO do aluno e os DADOS (lista JSON de linhas retornadas pelo banco) "
    "e escreva a resposta em Markdown, em português do Brasil. "
    "Use SOMENTE as informações presentes em DADOS; não invente exercícios, "
    "resumos nem resoluções. "
    "Escreva toda expressão matemática em LaTeX: inline com $...$ e em bloco com $$...$$."
)


class FormatterAgent:
    """Só formata: não consulta o banco nem valida LaTeX (isso é do orquestrador)."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def format(self, intent: Intent, rows: list[dict[str, Any]]) -> str:
        # default=str: o SQLite pode devolver bytes (BLOB) ou outros tipos sem JSON.
        dados = json.dumps(rows, ensure_ascii=False, default=str)
        user = build_blocks(INTENCAO=intent.value, DADOS=dados)
        return self._llm.complete(SYSTEM_PROMPT, user)
