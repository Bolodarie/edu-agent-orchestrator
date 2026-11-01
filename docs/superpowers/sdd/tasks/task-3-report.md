# Task 3 report: SQL validator (database.py part 1)

Status: DONE. Commit 4b6a663 "feat: add SQL SELECT validator" on branch task/t3-sql-validator (worktree edu-agent-orchestrator-wt/t3).

## Implementation (database.py)
Hand-written tokenizer (word/number/string/punct tokens with start positions), stdlib only, imports only `exceptions.SQLRejeitadoError`.
- Public: `ALLOWED_TABLES`, `MAX_LIMIT = 50`, `validate_select(sql, allowed_tables, max_limit) -> str`.
- `_tokenize`: respects '...' literals with '' escape; rejects `--` and `/* */` outside literals, unterminated literals, and quoted identifiers (`"`, backtick, `[`, `]`) as unsupported.
- `_strip_trailing_semicolon`: tolerates one final `;`, rejects any other (multiple statements).
- `_check_statement_start`: first word must be SELECT (empty rejected, WITH rejected).
- `_check_forbidden_words`: INSERT UPDATE DELETE DROP ALTER CREATE ATTACH DETACH PRAGMA REPLACE VACUUM, plus WITH anywhere (so CTE inside a subquery is rejected). Literals are single string tokens, so words inside them are ignored.
- `_check_tables`: tracks FROM state per parenthesis depth; the identifier after FROM/JOIN and after commas in a FROM list must be in the allowed list (case-insensitive); aliases accepted; `FROM (SELECT ...)` subqueries accepted, `FROM (Exercicios)`, `schema.table`, `table(` rejected; `IS DISTINCT FROM` is not treated as a table clause; parentheses must balance.
- `_check_final_limit`: last two tokens must be `LIMIT <digits>` (so OFFSET, `LIMIT a, b`, negatives, decimals are rejected), value <= max_limit; since parentheses are balanced this is top level.
- Returns the SQL up to the end of the last token, stripped (final `;` removed).
Docstring states it is not a full SQL parser and the read-only connection is the independent second barrier. No placeholder code for Task 4.

## Tests (tests/test_sql_validator.py)
All accept/reject cases from the brief, plus extras: comma joins to forbidden table, JOIN with forbidden table, quoted identifiers, `main.` qualification, OFFSET, `LIMIT a, b`, negative/decimal/non-numeric LIMIT, unbalanced parens, unterminated literal, `;;`, trailing statement keywords, WITH in subquery, `(Exercicios)`, EXPLAIN, PRAGMA, custom allowed_tables/max_limit, trailing `;` stripping, non-str input, case-insensitivity, `''` escape containing `;`/`--`/`/*`.

## TDD evidence
RED: `cd .../t3 && /home/igorg/facul/aprendizado/edu-agent-orchestrator/.venv/bin/python -m pytest tests/test_sql_validator.py -v`
-> `ModuleNotFoundError: No module named 'database'` ... `1 error in 0.07s` (collection error before implementation).
GREEN: same command -> `45 passed in 0.03s`. Full suite in worktree: `49 passed in 0.07s` (includes test_models.py).

## Files changed
database.py (new), tests/test_sql_validator.py (new). Nothing else touched; no push, no branch switch.

## Self-review / concerns
- Task 4 will add schema/seed/Database class to this file; the validator section is delimited by a header comment and uses private `_` helpers.
- Known limits (accepted, covered by read-only connection): `FROM` inside function-like syntax other than `IS DISTINCT FROM` would be treated as a table clause (false rejection, safe direction); non-listed functions/columns are not checked; unusual SQLite syntax (e.g. table-valued functions) is rejected rather than parsed.
- Forbidden list is the brief's list plus WITH-anywhere; a column/function named `replace` is rejected per the brief.

## Fix round 1 (review: Important finding on `_check_final_limit`)
Problem: `valor.isdigit()` accepted Unicode digits and `int()` could raise `ValueError` (e.g. `LIMIT 5²`, 5000-digit LIMIT), escaping as non-`SQLRejeitadoError`; `LIMIT 1٣` was accepted.
Change (database.py `_check_final_limit`): require `valor.isascii() and valor.isdigit()`; reject if `len(valor) > 18` before calling `int()`, then compare with max_limit.
Tests added (tests/test_sql_validator.py, `test_limit_nao_ascii_ou_gigante_levanta_sql_rejeitado`, 3 params): `LIMIT 5²`, `LIMIT 1٣`, 5000-digit LIMIT, all must raise SQLRejeitadoError.
RED: `.venv/bin/python -m pytest tests/test_sql_validator.py -q` -> `3 failed, 45 passed` (ValueError for the 5000-digit case; the two Unicode cases did not raise SQLRejeitadoError).
GREEN: same command -> 48 passed; full suite 52 passed.
Commit: "fix: reject non-ASCII and oversized LIMIT literals with SQLRejeitadoError". Minor review items not touched (deferred as instructed).
