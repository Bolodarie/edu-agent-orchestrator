from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Intent(str, Enum):
    BUSCAR_EXERCICIOS = "buscar_exercicios"
    BUSCAR_RESUMO = "buscar_resumo"
    BUSCAR_RESOLUCAO = "buscar_resolucao"
    FORA_DO_ESCOPO = "fora_do_escopo"


class RouterResult(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)


class QueryAttempt(BaseModel):
    sql: str
    error: str | None = None
    row_count: int | None = None


class Trace(BaseModel):
    intent: Intent | None = None
    confidence: float | None = None
    attempts: list[QueryAttempt] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
    tempos_ms: dict[str, float] = Field(default_factory=dict)


Status = Literal["ok", "fora_do_escopo", "sem_resultados", "erro"]


class OrchestratorResponse(BaseModel):
    text: str
    status: Status
    trace: Trace
