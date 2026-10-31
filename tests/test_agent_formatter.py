import json

from agents.formatter import FormatterAgent
from llm import MockLLMClient, parse_blocks
from models import Intent
from tests.fakes import FakeLLMClient


def test_serializa_linhas_em_json():
    rows = [{"nome": "Fatoração", "resumo_teorico": "Diferença de quadrados: $a^2-b^2$"}]
    llm = FakeLLMClient(["ok"])
    FormatterAgent(llm).format(Intent.BUSCAR_RESUMO, rows)
    _, user = llm.calls[0]
    assert "DADOS:" in user
    blocos = parse_blocks(user)
    assert blocos["INTENCAO"].strip() == Intent.BUSCAR_RESUMO.value
    assert json.loads(blocos["DADOS"]) == rows
    assert "Fatoração" in blocos["DADOS"]  # ensure_ascii=False


def test_devolve_saida_do_llm_intacta():
    llm = FakeLLMClient(["$$ x $$"])
    assert FormatterAgent(llm).format(Intent.BUSCAR_RESOLUCAO, [{"a": 1}]) == "$$ x $$"


def test_nao_valida_latex():
    saida = "preço de $ solto e $x"
    llm = FakeLLMClient([saida])
    assert FormatterAgent(llm).format(Intent.BUSCAR_RESUMO, []) == saida


def test_integracao_com_mock():
    saida = FormatterAgent(MockLLMClient()).format(
        Intent.BUSCAR_RESUMO,
        [{"nome": "Fatoração", "resumo_teorico": "Texto $a^2$"}],
    )
    assert "Texto $a^2$" in saida
