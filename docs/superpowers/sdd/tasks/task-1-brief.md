### Task 1: Scaffold, contratos e exceções

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `models.py`, `exceptions.py`, `agents/__init__.py`, `tests/__init__.py`, `tests/test_models.py`

**Interfaces:**
- Produces (`models.py`): `class Intent(str, Enum)` com `BUSCAR_EXERCICIOS="buscar_exercicios"`, `BUSCAR_RESUMO="buscar_resumo"`, `BUSCAR_RESOLUCAO="buscar_resolucao"`, `FORA_DO_ESCOPO="fora_do_escopo"`; `RouterResult(intent: Intent, confidence: float)` com `0 ≤ confidence ≤ 1`; `QueryAttempt(sql: str, error: str | None = None, row_count: int | None = None)`; `Trace(intent: Intent | None = None, confidence: float | None = None, attempts: list[QueryAttempt] = [], avisos: list[str] = [], tempos_ms: dict[str, float] = {})`; `Status = Literal["ok","fora_do_escopo","sem_resultados","erro"]`; `OrchestratorResponse(text: str, status: Status, trace: Trace)`.
- Produces (`exceptions.py`): `AgentPipelineError(Exception)` com atributo de classe `recuperavel: bool = False`; filhas `IntencaoDesconhecidaError` (False), `SQLRejeitadoError`, `SQLExecucaoError`, `SaidaDoAgenteInvalidaError` (as três True).

- [ ] **Step 1:** Criar `requirements.txt` (`streamlit`, `pydantic`), `requirements-dev.txt` (`-r requirements.txt`, `pytest`), `pytest.ini` (`testpaths = tests`, `pythonpath = .`); rodar `pip install -r requirements-dev.txt`.
- [ ] **Step 2: Write the failing tests** em `tests/test_models.py`:
  - `test_confidence_fora_do_intervalo_falha`: `RouterResult(intent=Intent.BUSCAR_RESUMO, confidence=1.5)` levanta `pydantic.ValidationError`.
  - `test_trace_defaults_nao_sao_compartilhados`: duas instâncias de `Trace()` não compartilham `attempts` (append em uma não afeta a outra).
  - `test_response_rejeita_status_invalido`: `OrchestratorResponse(text="x", status="qualquer", trace=Trace())` levanta `ValidationError`.
  - `test_recuperabilidade`: `SQLRejeitadoError.recuperavel is True`, `SQLExecucaoError.recuperavel is True`, `SaidaDoAgenteInvalidaError.recuperavel is True`, `IntencaoDesconhecidaError.recuperavel is False`; todas são subclasses de `AgentPipelineError`.
- [ ] **Step 3:** Rodar `pytest tests/test_models.py -v`. Esperado: FAIL (módulos inexistentes).
- [ ] **Step 4:** Implementar `models.py` e `exceptions.py` conforme Interfaces (Pydantic v2, `Field(default_factory=...)` para listas e dicts).
- [ ] **Step 5:** Rodar `pytest tests/test_models.py -v`. Esperado: 4 PASS.

---

