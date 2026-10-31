"""Contrato de prompt entre agentes e LLM, e o MockLLMClient determinístico.

Os prompts de usuário são blocos rotulados (``CHAVE:`` em linha própria). O mock
lê esses rótulos; uma LLM real os lê como texto comum. Este módulo só depende de
``models.Intent`` (nada de banco, agentes ou orquestrador).
"""

import json
import re
import unicodedata
from typing import Protocol

from models import Intent

# --- Rótulos do contrato (spec 6.1) -------------------------------------------------
PERGUNTA = "PERGUNTA"
INTENCAO = "INTENCAO"
SCHEMA = "SCHEMA"
SQL_ANTERIOR = "SQL_ANTERIOR"
ERRO_ANTERIOR = "ERRO_ANTERIOR"
DADOS = "DADOS"

_KEY_RE = re.compile(r"[A-Z_]+")
_LABEL_LINE_RE = re.compile(r"[A-Z_]+:")  # cabeçalho de bloco: linha inteira
_FORGED_LABEL_RE = re.compile(r" *[A-Z_]+:")  # conteúdo que lembra rótulo
_NEUTRALIZED_RE = re.compile(r" +[A-Z_]+:")


def build_blocks(**blocos: str) -> str:
    """Monta o prompt: cada chave vira ``CHAVE:`` sozinha numa linha, seguida das
    linhas do conteúdo. Linhas de conteúdo que pareçam rótulo ganham um espaço
    inicial para que texto do usuário não consiga forjar rótulos."""
    linhas: list[str] = []
    for chave, conteudo in blocos.items():
        if not _KEY_RE.fullmatch(chave):
            raise ValueError(f"rótulo inválido: {chave!r}")
        linhas.append(f"{chave}:")
        for linha in conteudo.split("\n"):
            if _FORGED_LABEL_RE.match(linha):
                linha = " " + linha
            linhas.append(linha)
    return "\n".join(linhas)


def parse_blocks(prompt: str) -> dict[str, str]:
    """Inverso de ``build_blocks``. Texto antes do primeiro rótulo é ignorado."""
    blocos: dict[str, list[str]] = {}
    atual: list[str] | None = None
    for linha in prompt.split("\n"):
        if _LABEL_LINE_RE.fullmatch(linha):
            atual = blocos.setdefault(linha[:-1], [])
        elif atual is not None:
            if _NEUTRALIZED_RE.match(linha):
                linha = linha[1:]
            atual.append(linha)
    return {chave: "\n".join(linhas) for chave, linhas in blocos.items()}


_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*[ \t]*\n?(.*?)\n?```$", re.DOTALL)


def strip_code_fences(texto: str) -> str:
    """Remove uma cerca de código que envolva a saída inteira (com ou sem tag de
    linguagem); sem cerca, devolve o texto apenas sem espaços nas pontas."""
    texto = texto.strip()
    achado = _FENCE_RE.match(texto)
    return achado.group(1).strip() if achado else texto


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


# --- Normalização e catálogo de tópicos (spec 6.2) ----------------------------------
def _normalize(texto: str) -> str:
    """Minúsculas, sem acentos; ordinais (º, °) viram 'o' ('2º' -> '2o')."""
    decomposto = unicodedata.normalize("NFD", texto.lower())
    sem_acentos = "".join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r"[º°]", "o", sem_acentos)


# fragmento (usado em LIKE sobre Topicos_Algebra.nome) -> apelidos já normalizados
_TOPICOS: dict[str, tuple[str, ...]] = {
    "1º Grau": ("1o grau", "1 grau", "primeiro grau"),
    "2º Grau": ("2o grau", "2 grau", "segundo grau", "bhaskara", "baskara"),
    "Sistemas": ("sistemas", "sistema", "sistemas lineares", "sistema linear"),
    "Fatoração": ("fatoracao", "fatorar", "fatoracao de polinomios"),
    # Ausente do seed de propósito: exercita o caminho `sem_resultados` (spec 6.2).
    "Logaritmo": ("logaritmo", "log"),
}


def _alias_re(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")


_TOPICO_PADROES = [
    (fragmento, [_alias_re(a) for a in apelidos])
    for fragmento, apelidos in _TOPICOS.items()
]


def _find_topic(pergunta: str) -> str | None:
    """Fragmento do primeiro tópico citado (menor posição no texto) ou None."""
    texto = _normalize(pergunta)
    melhor: tuple[int, str] | None = None
    for fragmento, padroes in _TOPICO_PADROES:
        for padrao in padroes:
            achado = padrao.search(texto)
            if achado and (melhor is None or achado.start() < melhor[0]):
                melhor = (achado.start(), fragmento)
    return melhor[1] if melhor else None


# --- Roteador ------------------------------------------------------------------------
# `resolv` cobre resolver/resolva/resolve (ampliação do `resolu`/`resolver` da spec).
_RE_RESOLUCAO = re.compile(r"\bresolu|\bresolv")
_RE_RESUMO = re.compile(r"\bresumo|\bteoria")
_RE_EXERCICIOS = re.compile(r"\bexercicio|\bquest(?:ao|oes)\b|\blista")


def _route(pergunta: str) -> dict:
    texto = _normalize(pergunta)
    if _RE_RESOLUCAO.search(texto):
        intent, confidence = Intent.BUSCAR_RESOLUCAO, 0.9
    elif _RE_RESUMO.search(texto):
        intent, confidence = Intent.BUSCAR_RESUMO, 0.9
    elif _RE_EXERCICIOS.search(texto):
        intent, confidence = Intent.BUSCAR_EXERCICIOS, 0.9
    elif _find_topic(pergunta) is not None:
        intent, confidence = Intent.BUSCAR_EXERCICIOS, 0.7
    else:
        intent, confidence = Intent.FORA_DO_ESCOPO, 0.8
    return {"intent": intent.value, "confidence": confidence}


# --- Consulta (spec 6.3) -------------------------------------------------------------
_SQL_SEM_LIMITE_RUIM = "SELECT * FROM Exercicios"  # gancho 'teste retry'

_SELECTS = {
    Intent.BUSCAR_EXERCICIOS: (
        "SELECT t.nome, e.enunciado_latex, e.dificuldade "
        "FROM Exercicios e JOIN Topicos_Algebra t ON t.id = e.topico_id",
        5,
    ),
    Intent.BUSCAR_RESUMO: (
        "SELECT t.nome, t.resumo_teorico FROM Topicos_Algebra t",
        3,
    ),
    Intent.BUSCAR_RESOLUCAO: (
        "SELECT t.nome, e.enunciado_latex, r.passo_a_passo_latex "
        "FROM Resolucoes r "
        "JOIN Exercicios e ON e.id = r.exercicio_id "
        "JOIN Topicos_Algebra t ON t.id = e.topico_id",
        3,
    ),
}


def _build_sql(blocos: dict[str, str]) -> str:
    pergunta = blocos.get(PERGUNTA, "")
    if "teste retry" in _normalize(pergunta) and ERRO_ANTERIOR not in blocos:
        return _SQL_SEM_LIMITE_RUIM
    try:
        intent = Intent(blocos.get(INTENCAO, "").strip())
    except ValueError:
        intent = Intent.BUSCAR_EXERCICIOS
    base, limite = _SELECTS.get(intent, _SELECTS[Intent.BUSCAR_EXERCICIOS])
    fragmento = _find_topic(pergunta)
    where = f" WHERE t.nome LIKE '%{fragmento}%'" if fragmento else ""
    return f"{base}{where} LIMIT {limite}"


# --- Formatador ----------------------------------------------------------------------
def _math(latex: str) -> str:
    return f"$$\n{latex}\n$$"


def _format(blocos: dict[str, str]) -> str:
    try:
        intent = Intent(blocos.get(INTENCAO, "").strip())
    except ValueError:
        intent = Intent.BUSCAR_EXERCICIOS
    linhas = json.loads(blocos.get(DADOS, "[]"))
    if not linhas:
        return "Não encontrei nada para mostrar."

    partes: list[str] = []
    if intent is Intent.BUSCAR_RESUMO:
        partes.append("Aqui está o resumo teórico:")
        for linha in linhas:
            partes.append(f"### {linha.get('nome', '')}\n\n{linha.get('resumo_teorico', '')}")
    elif intent is Intent.BUSCAR_RESOLUCAO:
        partes.append("Aqui está a resolução passo a passo:")
        for i, linha in enumerate(linhas, 1):
            partes.append(
                f"### {i}. {linha.get('nome', '')}\n\n"
                f"**Enunciado**\n\n{_math(linha.get('enunciado_latex', ''))}\n\n"
                f"**Resolução**\n\n{_math(linha.get('passo_a_passo_latex', ''))}"
            )
    else:
        partes.append("Aqui estão os exercícios:")
        for i, linha in enumerate(linhas, 1):
            partes.append(
                f"### {i}. {linha.get('nome', '')} "
                f"(dificuldade: {linha.get('dificuldade', '')})\n\n"
                f"{_math(linha.get('enunciado_latex', ''))}"
            )
    return "\n\n".join(partes)


# --- Mock ----------------------------------------------------------------------------
class MockLLMClient:
    """LLM determinística. Despacha pelos rótulos do prompt de usuário:
    ``DADOS`` -> formatador; ``SCHEMA`` -> consulta; senão -> roteador."""

    def complete(self, system: str, user: str) -> str:
        blocos = parse_blocks(user)
        if DADOS in blocos:
            return _format(blocos)
        if SCHEMA in blocos:
            return _build_sql(blocos)
        return json.dumps(_route(blocos.get(PERGUNTA, "")))
