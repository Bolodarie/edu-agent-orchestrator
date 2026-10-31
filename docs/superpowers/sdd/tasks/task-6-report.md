# Task 6 report: RouterAgent + shared FakeLLMClient

Status: DONE

## Implementation
- `agents/router.py`: `SYSTEM_PROMPT` (constant, lists all `Intent` values, demands JSON `{"intent","confidence"}`), `_strip_fences` (regex removing ```` ``` ````/```` ```json ```` fences), `RouterAgent(llm)` with `classify(pergunta) -> RouterResult`. User prompt built only via `build_blocks(PERGUNTA=...)`. `json.JSONDecodeError` (a ValueError), non-object JSON, and pydantic `ValidationError` (bad enum / confidence out of range) are all converted to `IntencaoDesconhecidaError` (message in pt-BR, chained `from exc`). Imports only `llm`, `models`, `exceptions` (+ pydantic, stdlib).
- `tests/fakes.py`: `FakeLLMClient(respostas)`; `calls: list[tuple[str,str]]`; returns responses in order, repeats the last; `ValueError` on empty list. Satisfies `LLMClient` Protocol.
- `tests/test_agent_router.py`: imports the fake from `tests.fakes`. 8 tests: the 6 from the brief plus `test_json_que_nao_e_objeto` and a test of the fake (repeat-last, empty-list error). `test_envia_pergunta_no_prompt` also asserts all intent values appear in the system prompt.

## TDD evidence
RED: `.venv/bin/python -m pytest tests/test_agent_router.py -v` -> `ModuleNotFoundError: No module named 'agents.router'` (collection error, 1 error).
GREEN: same command -> `8 passed in 0.05s`. Full suite: `117 passed in 0.15s`.
Sanity: `RouterAgent(MockLLMClient()).classify('resumo de 2º grau')` returns a valid RouterResult (buscar_resumo, 0.9).

## Files changed
agents/router.py, tests/fakes.py, tests/test_agent_router.py (nothing else touched).

## Self-review
- Fence regex handles ```` ```json\n{...}\n``` ```` and bare fences; unfenced text passes through unchanged.
- The fake records the call before returning, index = min(len(calls), len-1) so exhaustion repeats the last response.
- No attribution in commit.

## Concerns
None. Note: `PERGUNTA` constant imported from `llm` and passed as `**{PERGUNTA: pergunta}` (equivalent to `PERGUNTA=pergunta`).
