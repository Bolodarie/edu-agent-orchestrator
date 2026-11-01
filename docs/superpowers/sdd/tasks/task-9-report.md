# Task 9 report: orchestrator.py

Status: DONE

## Implementation
`orchestrator.py` (new): `Orchestrator(router, query_agent, formatter, database, max_attempts=3)` with `handle(texto)`, and `build_orchestrator(db_path="data/edu.db")`.
- Empty/whitespace input returns `fora_do_escopo` before anything is called (no LLM, no DB).
- `handle` is the only place that catches `AgentPipelineError` (outer try/except -> `erro`, with `"<ExcName>: <msg>"` appended to `trace.avisos`).
- `_consultar` loops up to `max_attempts`: generate SQL (passes `sql_anterior`/`erro_anterior` from attempt 2), execute, record a `QueryAttempt` (with `row_count` on success, `error` on failure; `sql=""` when generation itself failed). Recoverable errors continue; non-recoverable errors are recorded then re-raised to `handle`. Exhausted -> `erro`.
- Zero rows -> `sem_resultados` (formatter not called). Otherwise format -> `validate_latex` -> `ok`, warnings extended into `trace.avisos`.
- Timings via `time.perf_counter` in a small `_medir` context manager; keys `roteador`, `consulta`, `banco`, `formatador`, `latex` (accumulated across retries, only those that ran).
- Student-facing Portuguese constants: `MSG_FORA_DO_ESCOPO`, `MSG_SEM_RESULTADOS`, `MSG_ERRO`.

`tests/test_orchestrator.py` (new): 14 test cases (the brief's 11 test functions; two are parametrized: resumo/resolucao x2, entrada vazia x2; plus one extra `test_max_attempts_configuravel`). No change to tests/fakes.py.

## TDD evidence
RED: `.venv/bin/python -m pytest tests/test_orchestrator.py -q` -> `ModuleNotFoundError: No module named 'orchestrator'` (collection error).
GREEN: same command with -v -> `14 passed in 0.10s`.
Full suite: `.venv/bin/python -m pytest -q` -> `150 passed in 0.21s`.

## Files changed
- /home/igorg/facul/aprendizado/edu-agent-orchestrator/orchestrator.py
- /home/igorg/facul/aprendizado/edu-agent-orchestrator/tests/test_orchestrator.py

## Self-review
- Retry demo works end to end with the real MockLLMClient (attempt 1: `SELECT * FROM Exercicios` rejected by the validator; attempt 2 ok).
- Review Focus 1 proven with spy Fakes (0 LLM calls) and a `Database` subclass counting `execute_readonly` calls (0).
- Test for the retry prompt confirms `SQL_ANTERIOR`/`ERRO_ANTERIOR` are absent on call 1 and present on call 2.

## Concerns
- None blocking. The architecture boundary test mentioned in CLAUDE.md (ast-based) doesn't exist yet; orchestrator.py imports agents/database/llm/latex_validator together, as allowed.
- `trace.avisos` is reused to carry the technical error detail for non-attempt failures (router error, formatter error); there is no dedicated trace field for it.
- Commit made on feat/poc-implementation, no attribution trailer.
