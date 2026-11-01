import pytest

from agents.router import RouterAgent
from exceptions import IntencaoDesconhecidaError
from models import Intent, RouterResult
from tests.fakes import FakeLLMClient


def test_classifica_json_valido():
    llm = FakeLLMClient(['{"intent":"buscar_resumo","confidence":0.8}'])
    resultado = RouterAgent(llm).classify("Me dê um resumo de 2º grau")
    assert resultado == RouterResult(intent=Intent.BUSCAR_RESUMO, confidence=0.8)


def test_aceita_json_em_cerca():
    llm = FakeLLMClient(['```json\n{"intent":"buscar_exercicios","confidence":0.9}\n```'])
    resultado = RouterAgent(llm).classify("exercícios de sistemas")
    assert resultado.intent is Intent.BUSCAR_EXERCICIOS
    assert resultado.confidence == 0.9


def test_json_malformado():
    with pytest.raises(IntencaoDesconhecidaError):
        RouterAgent(FakeLLMClient(["não sei"])).classify("oi")


def test_json_que_nao_e_objeto():
    with pytest.raises(IntencaoDesconhecidaError):
        RouterAgent(FakeLLMClient(["[1, 2]"])).classify("oi")


def test_intencao_fora_do_enum():
    llm = FakeLLMClient(['{"intent":"apagar_tudo","confidence":1}'])
    with pytest.raises(IntencaoDesconhecidaError):
        RouterAgent(llm).classify("apague tudo")


def test_confianca_invalida():
    llm = FakeLLMClient(['{"intent":"buscar_resumo","confidence":7}'])
    with pytest.raises(IntencaoDesconhecidaError):
        RouterAgent(llm).classify("resumo")


def test_envia_pergunta_no_prompt():
    llm = FakeLLMClient(['{"intent":"fora_do_escopo","confidence":0.5}'])
    RouterAgent(llm).classify("qual a capital da França?")
    (system, user), = llm.calls
    assert "PERGUNTA:" in user
    assert "qual a capital da França?" in user
    for intent in Intent:
        assert intent.value in system


def test_fake_repete_ultima_resposta_e_rejeita_lista_vazia():
    llm = FakeLLMClient(["a", "b"])
    assert [llm.complete("s", "u") for _ in range(3)] == ["a", "b", "b"]
    with pytest.raises(ValueError):
        FakeLLMClient([])
