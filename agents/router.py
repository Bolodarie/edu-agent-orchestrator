"""Agente roteador: classifica a pergunta do aluno em uma ``Intent``."""

import json
import re

from pydantic import ValidationError

from exceptions import IntencaoDesconhecidaError
from llm import PERGUNTA, LLMClient, build_blocks
from models import Intent, RouterResult

_INTENTS = ", ".join(f'"{i.value}"' for i in Intent)

SYSTEM_PROMPT = (
    "Você é o roteador de um assistente de álgebra para estudantes. "
    "Classifique a PERGUNTA do aluno em exatamente uma das intenções válidas: "
    f"{_INTENTS}. "
    'Use "fora_do_escopo" para qualquer pedido que não seja sobre exercícios, '
    "resumos teóricos ou resoluções de álgebra. "
    'Responda SOMENTE com JSON no formato {"intent": "<intenção>", "confidence": <número de 0 a 1>}, '
    "sem texto adicional."
)

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*[ \t]*\n?(.*?)\n?```$", re.DOTALL)


def _strip_fences(texto: str) -> str:
    texto = texto.strip()
    achado = _FENCE_RE.match(texto)
    return achado.group(1).strip() if achado else texto


class RouterAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def classify(self, pergunta: str) -> RouterResult:
        bruto = self._llm.complete(SYSTEM_PROMPT, build_blocks(**{PERGUNTA: pergunta}))
        try:
            dados = json.loads(_strip_fences(bruto))
            if not isinstance(dados, dict):
                raise ValueError("a resposta do roteador não é um objeto JSON")
            return RouterResult.model_validate(dados)
        except (ValueError, ValidationError) as exc:
            raise IntencaoDesconhecidaError(
                f"Não consegui entender a intenção da pergunta: {exc}"
            ) from exc
