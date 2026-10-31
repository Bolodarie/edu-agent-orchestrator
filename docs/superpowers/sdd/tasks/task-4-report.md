# Task 4 report: schema, seed e execução somente leitura

Status: DONE. Commit bf82f64 "feat: add schema, seed and read-only Database execution" (worktree t4, branch task/t4-database, base 15902db). Files: database.py (modified), tests/test_database.py (new).

## Implementation
- database.py: docstring/imports updated (sqlite3, Path, typing, SQLExecucaoError); validator code untouched (only the module docstring header lines and the import line were removed/replaced).
- SCHEMA_DESCRIPTION (pt-BR, 3 tables/columns), _SCHEMA_SQL (CREATE TABLE IF NOT EXISTS), _SEED data constants (4 topics: Equação do 1º Grau, Equação do 2º Grau, Sistemas Lineares, Fatoração; 3 exercises each, difficulties fácil/média/difícil, one resolution per exercise). Math columns are pure LaTeX with no `$`, no blank lines, aligned blocks built by `_aligned()`; resumos are Markdown with inline `$...$`.
- Database(path): `ensure_ready()` mkdirs parent, uses a separate write connection (only place with writes), schema + seed in ONE explicit transaction (ROLLBACK on error), seeds only if Topicos_Algebra is empty, hence idempotent and also heals an existing empty file. `PRAGMA foreign_keys=ON` on the write connection.
- `execute_readonly()`: `validate_select` first (SQLRejeitadoError propagates untouched), then `file:<resolved abs path as_uri>?mode=ro` with `uri=True` (as_uri percent-encodes spaces/#/?), dict row_factory, connection closed in finally; only `sqlite3.Error` -> SQLExecucaoError (chained). `enable_load_extension` is never called (documented in module docstring + test).
- `schema_description` attribute = SCHEMA_DESCRIPTION. database.py imports only stdlib + exceptions.

## Tests (tests/test_database.py, 14 tests)
Brief's 7 tests plus: dificuldades do seed, cria diretório pai, SQLRejeitado não vira SQLExecucao, load_extension -> SQLExecucaoError (extensions not enabled), banco inexistente -> SQLExecucaoError, schema_description cobre tabelas/colunas, resoluções do seed quebram linha com `\\`.
Result: `pytest tests/test_database.py tests/test_sql_validator.py -v` -> 62 passed. Full `pytest -q` in worktree -> 78 passed.

## TDD evidence
RED: `python -m pytest tests/test_database.py -v` before implementation -> `ImportError: cannot import name 'SCHEMA_DESCRIPTION' from 'database'` (collection error, 1 error).
GREEN: after implementation, 61 passed (13 db tests + validator).
Self-review RED/GREEN #2: first draft of `_aligned` emitted a single backslash line break (my generation script's escaping bug); the original LaTeX-validity test did NOT catch it (balanced delimiters only). Added `test_resolucoes_do_seed_quebram_linhas_com_barra_dupla`; with the bug reintroduced it fails (`1 failed, 13 passed`), after fix 62 passed.

## Concerns / notes
- Brief says `file:{path}?mode=ro`; I used `Path.resolve().as_uri()` for robustness. test_conexao_e_somente_leitura still uses the plain form per brief.
- The validator's test uses column `enunciado` in some accepted-SQL cases; irrelevant (validator doesn't check columns). Real column is `enunciado_latex` per spec 6.3.
- A pre-existing non-empty DB with the schema but different content is left untouched (no re-seed), by design.
