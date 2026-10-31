import pytest
from pydantic import ValidationError

from exceptions import (
    AgentPipelineError,
    IntencaoDesconhecidaError,
    SaidaDoAgenteInvalidaError,
    SQLExecucaoError,
    SQLRejeitadoError,
)
from models import Intent, OrchestratorResponse, QueryAttempt, RouterResult, Trace


def test_confidence_fora_do_intervalo_falha():
    with pytest.raises(ValidationError):
        RouterResult(intent=Intent.BUSCAR_RESUMO, confidence=1.5)


def test_trace_defaults_nao_sao_compartilhados():
    a = Trace()
    b = Trace()
    a.attempts.append(QueryAttempt(sql="SELECT 1"))
    a.avisos.append("y")
    a.tempos_ms["k"] = 1.0
    assert b.attempts == []
    assert b.avisos == []
    assert b.tempos_ms == {}


def test_response_rejeita_status_invalido():
    with pytest.raises(ValidationError):
        OrchestratorResponse(text="x", status="qualquer", trace=Trace())


def test_recuperabilidade():
    assert SQLRejeitadoError.recuperavel is True
    assert SQLExecucaoError.recuperavel is True
    assert SaidaDoAgenteInvalidaError.recuperavel is True
    assert IntencaoDesconhecidaError.recuperavel is False
    for exc in (
        IntencaoDesconhecidaError,
        SQLRejeitadoError,
        SQLExecucaoError,
        SaidaDoAgenteInvalidaError,
    ):
        assert issubclass(exc, AgentPipelineError)
