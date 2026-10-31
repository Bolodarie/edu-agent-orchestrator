# Task 8 report: agents/formatter.py

Status: DONE

## Implementation
`agents/formatter.py`: `FormatterAgent(llm)` with `format(intent, rows) -> str`. User prompt is built only via
`build_blocks(INTENCAO=intent.value, DADOS=json.dumps(rows, ensure_ascii=False))`; the system prompt (pt-BR) tells the
LLM to use only DADOS and write LaTeX with `$...$` / `$$...$$`. Returns `llm.complete(...)` unchanged (no LaTeX
validation). Imports only `llm`, `models` (plus stdlib); no `database`.

## Tests (`tests/test_agent_formatter.py`, 4)
- test_serializa_linhas_em_json (parse_blocks + json.loads round-trip, accents preserved, INTENCAO checked)
- test_devolve_saida_do_llm_intacta
- test_nao_valida_latex
- test_integracao_com_mock
Uses `tests.fakes.FakeLLMClient`; no new fake.

## TDD evidence
RED: `pytest tests/test_agent_formatter.py -v` -> `ModuleNotFoundError: No module named 'agents.formatter'` (collection error, 1 error).
GREEN: same command -> `4 passed in 0.05s`. Full suite in worktree: `121 passed`.

## Files changed
- agents/formatter.py (new)
- tests/test_agent_formatter.py (new)

## Commit
Branch task/t8-formatter, commit "feat: add FormatterAgent" (no attribution trailer).

## Self-review
Matches brief and controller rulings. No concerns. Note: the real `MockLLMClient` formatter branch was exercised
(integration test passes), confirming DADOS format compatibility.
