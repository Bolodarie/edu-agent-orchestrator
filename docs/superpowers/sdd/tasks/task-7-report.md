# Task 7 report: agents/query.py (QueryAgent)

Status: DONE. Commit 151a0a1 "feat: add QueryAgent" on branch task/t7-query (worktree /home/igorg/facul/aprendizado/edu-agent-orchestrator-wt/t7).

## Implementation
agents/query.py: `SYSTEM_PROMPT` (pt-BR), `QueryAgent(llm)` and `generate_sql(pergunta, intent, schema, sql_anterior=None, erro_anterior=None) -> str`.
- User prompt built only via `build_blocks` with PERGUNTA, INTENCAO (intent.value), SCHEMA. SQL_ANTERIOR/ERRO_ANTERIOR keys are omitted entirely on first attempt; both are added only when BOTH are provided.
- Output: strip whitespace, strip ``` fences (same regex as router), then empty or no `\bselect\b` (case-insensitive) -> SaidaDoAgenteInvalidaError (pt-BR message).
- Imports only llm, models, exceptions (+ re). No `database`.

## Tests (tests/test_agent_query.py, uses tests.fakes.FakeLLMClient, parse_blocks for assertions)
8 tests (6 brief tests, saida_vazia parametrized over 2 inputs, plus one extra: only erro_anterior given -> no correction blocks).

RED: `python -m pytest tests/test_agent_query.py -v` -> `ModuleNotFoundError: No module named 'agents.query'` (collection error, 1 error).
GREEN: same command -> `8 passed in 0.05s`. Full suite in worktree: `125 passed in 0.19s`.

## Files changed
- agents/query.py (new)
- tests/test_agent_query.py (new)

## Self-review / concerns
- Fence stripper is duplicated from agents/router.py (not imported across agents, to respect the import constraint); candidate for a shared helper later.
- SELECT check is lenient by design (prose containing the word "select" would pass); SQL validator downstream (Task 3) is the real gate.
- Fences surrounded by prose are not extracted (only whole-output fences), matching the router.

## Fix round 1/5: duplicated fence stripping (Important)
Commit: refactor: share strip_code_fences via llm module (on top of 151a0a1).
- llm.py: added public `strip_code_fences(texto)` and `_FENCE_RE`, moved unchanged from the agents (no mid-prose extraction).
- agents/router.py and agents/query.py: removed private `_FENCE_RE`/`_strip_fences`, now `from llm import ... strip_code_fences`. Import sets still within llm/models/exceptions. Router's now-unused `import re` removed.
- New tests/test_llm_fences.py (7 tests): bare fence, ```json fence, no newline before closing fence, no-fence text stripped, no-fence text unchanged, empty string, empty fence.
- RED: tests/test_llm_fences.py -> ImportError: cannot import name 'strip_code_fences' from 'llm'.
- GREEN: `python -m pytest tests/test_llm_fences.py tests/test_agent_query.py tests/test_agent_router.py tests/test_llm_mock.py -v` -> 54 passed in 0.08s. Full suite: 132 passed. Existing test assertions untouched.
