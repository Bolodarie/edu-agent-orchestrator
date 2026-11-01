# Task 5 report: llm.py (contrato de prompt, LLMClient, MockLLMClient)

Status: DONE
Worktree: /home/igorg/facul/aprendizado/edu-agent-orchestrator-wt/t5 (branch task/t5-llm, base 15902db)
Commit: a015cc3 feat: add llm prompt-block contract, LLMClient protocol and MockLLMClient

## Implementation (llm.py)
- Label constants (PERGUNTA, INTENCAO, SCHEMA, SQL_ANTERIOR, ERRO_ANTERIOR, DADOS).
- `build_blocks(**blocos)`: writes `KEY:` alone on a line then content lines; keys validated against `[A-Z_]+`. Any content line matching `^ *[A-Z_]+:` gets one extra leading space. (Using ` *` rather than just `^[A-Z_]+:` makes the transform an exact inverse even for content lines that already start with spaces plus a label.)
- `parse_blocks(prompt)`: a header is a line matching `^[A-Z_]+:$` exactly; other lines belong to the current block; lines matching `^ +[A-Z_]+:` lose one leading space. Exact inverse of build_blocks (tested with multi-line, trailing newline, empty block, forged labels).
- `LLMClient(Protocol)` with `complete(system, user) -> str`.
- `MockLLMClient.complete`: DADOS -> formatter; else SCHEMA -> query; else router.
- Normalization: lowercase + NFD accent stripping; ordinal signs (º, °) mapped to "o" so "2º grau" -> "2o grau" (aliases are stored normalized).
- Router: regex precedence resolu/resolver > resumo/teoria > exercicio/questao/lista > known topic only > fora_do_escopo. Prefix word boundaries so e.g. "especialista" does not match "lista". Confidences: 0.9 keyword, 0.7 topic-only, 0.8 out of scope.
- Topic catalog dict fragment -> aliases: `1º Grau` (1o grau, 1 grau, primeiro grau), `2º Grau` (2o grau, 2 grau, segundo grau, bhaskara, baskara), `Sistemas` (sistema(s), sistema(s) linear(es)), `Fatoração` (fatoracao, fatorar, ...). Earliest match in the text wins; matching uses non-word boundaries.
- Query: SQL per spec 6.3 with `JOIN ... ON` and aliases, optional `WHERE t.nome LIKE '%<fragmento>%'`, LIMIT 5/3/3. Retry hook: normalized PERGUNTA contains "teste retry" and no ERRO_ANTERIOR block -> exactly `SELECT * FROM Exercicios`. Unknown/missing INTENCAO falls back to the exercises query.
- Formatter: reads INTENCAO + DADOS (JSON list); exercises show `### n. nome (dificuldade: x)` + `$$\n{math}\n$$`; resolution shows enunciado and passo a passo as `$$` blocks; summary passes `resumo_teorico` through unchanged. Empty data -> "Não encontrei nada para mostrar." Malformed DADOS JSON raises (json error propagates, deliberately loud for a test double).
- Imports: only stdlib + `models.Intent`. All mock text in pt-BR.

## Tests (tests/test_llm_mock.py, 31 cases)
All brief tests plus: roundtrip with label-like lines, Protocol conformance, router confidence shape, topic catalog/aliases parametrized, "teste retry" does not change intent, summary passthrough, resolution formatter. `validate_select` imported from `database` only in the test.

## TDD evidence
RED: `/home/igorg/facul/aprendizado/edu-agent-orchestrator/.venv/bin/python -m pytest tests/test_llm_mock.py -v`
```
tests/test_llm_mock.py:6: in <module>
    from llm import LLMClient, MockLLMClient, build_blocks, parse_blocks
E   ModuleNotFoundError: No module named 'llm'
1 error in 0.08s
```
GREEN (same command): `31 passed in 0.07s`. Full suite in the worktree: `95 passed in 0.11s`.

## Files changed
- /home/igorg/facul/aprendizado/edu-agent-orchestrator-wt/t5/llm.py (new)
- /home/igorg/facul/aprendizado/edu-agent-orchestrator-wt/t5/tests/test_llm_mock.py (new)

## Self-review / concerns
- No blocking concerns. Notes for later tasks: (1) the LIKE literals contain non-ASCII (`º`, `ç`, `ã`); validate_select accepts them (test passes), and SQLite LIKE is case-insensitive only for ASCII, so the seed names must use exactly `1º Grau`, `2º Grau`, `Sistemas`, `Fatoração` casing/accents (the seed names given in the plan do). (2) The neutralization changes the text an agent's real LLM sees only by one leading space on label-looking lines. (3) Agents must pass blocks via `build_blocks` and parse nothing themselves; the retry detection relies on the presence of the ERRO_ANTERIOR key, so agents must omit that key (not pass an empty string) on the first attempt.
