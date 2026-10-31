import pytest

from agents.query import QueryAgent
from exceptions import SaidaDoAgenteInvalidaError
from llm import parse_blocks
from models import Intent
from tests.fakes import FakeLLMClient

SCHEMA = "Tabela Exercicios(id, topico_id, enunciado_latex, dificuldade)"


def _gerar(resposta, **kwargs):
    llm = FakeLLMClient([resposta])
    sql = QueryAgent(llm).generate_sql(
        "quero exercícios de 2º grau", Intent.BUSCAR_EXERCICIOS, SCHEMA, **kwargs
    )
    return sql, llm


def test_devolve_sql_limpo():
    sql, _ = _gerar("```sql\nSELECT 1 LIMIT 1\n```")
    assert sql == "SELECT 1 LIMIT 1"


@pytest.mark.parametrize("saida", ["", "```\n```"])
def test_saida_vazia(saida):
    with pytest.raises(SaidaDoAgenteInvalidaError):
        _gerar(saida)


def test_saida_em_prosa():
    with pytest.raises(SaidaDoAgenteInvalidaError):
        _gerar("Claro! Aqui está sua consulta.")


def test_primeira_tentativa_nao_envia_bloco_de_erro():
    _, llm = _gerar("SELECT 1 LIMIT 1")
    blocos = parse_blocks(llm.calls[0][1])
    assert "ERRO_ANTERIOR" not in blocos
    assert "SQL_ANTERIOR" not in blocos


def test_correcao_envia_sql_e_erro():
    _, llm = _gerar(
        "SELECT 1 LIMIT 1", sql_anterior="SELECT 1", erro_anterior="sem LIMIT"
    )
    blocos = parse_blocks(llm.calls[0][1])
    assert blocos["SQL_ANTERIOR"] == "SELECT 1"
    assert blocos["ERRO_ANTERIOR"] == "sem LIMIT"


def test_envia_intencao_e_schema():
    _, llm = _gerar("SELECT 1 LIMIT 1")
    blocos = parse_blocks(llm.calls[0][1])
    assert blocos["INTENCAO"] == "buscar_exercicios"
    assert blocos["SCHEMA"] == SCHEMA
    assert blocos["PERGUNTA"] == "quero exercícios de 2º grau"


def test_apenas_um_dos_dois_nao_envia_bloco_de_correcao():
    _, llm = _gerar("SELECT 1 LIMIT 1", erro_anterior="sem LIMIT")
    blocos = parse_blocks(llm.calls[0][1])
    assert "ERRO_ANTERIOR" not in blocos
    assert "SQL_ANTERIOR" not in blocos
