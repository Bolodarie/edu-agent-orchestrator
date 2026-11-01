# Final fix wave report

Commits (branch feat/poc-implementation):
- 08cfa35 fix: reject non-ASCII whitespace and control chars in SQL validator
- 50f0aa5 fix: contain unexpected errors in handle(), serialize non-JSON rows, test real read-only barrier
- 8d3618f refactor: anchor default DB path, widen resolve matching, add Logaritmo mock topic, harden architecture and ensure_ready
- 5931025 docs: fix dev install command, note git repo, DB path and new mock topic

## Important 1 (database.py tokenizer)
- Change: `_tokenize` now skips only ASCII whitespace (`_ASCII_WHITESPACE = " \t\n\r\f"`); any other `isspace()` or non-printable char outside string literals raises SQLRejeitadoError("caractere não suportado fora de texto: ...").
- Deviation: `\v` is NOT in the whitelist (brief listed it). Verified empirically with sqlite3 that `LIMIT\v2` fails in SQLite ("unrecognized token") while \t \n \f \r work, so keeping \v out is stricter and consistent with SQLite.
- RED: `pytest tests/test_sql_validator.py` -> "7 failed, 50 passed" (NBSP, U+2003, U+2028, \x85, \x00, \x1f, embedded NUL: DID NOT RAISE).
- GREEN: 58 passed. Also added `execute_readonly` tests for `LIMIT\xa05` and NUL (SQLRejeitadoError), positive tests for ASCII whitespace and for `LIKE '%Fatoração%'` / NBSP inside a literal.

## Important 2 (error containment)
- Changes: `Orchestrator.handle` has a final `except Exception` -> status "erro", MSG_ERRO text, `trace.avisos` gets `Type: msg`; `FormatterAgent.format` uses `json.dumps(..., ensure_ascii=False, default=str)`; `execute_readonly` catches `(sqlite3.Error, sqlite3.Warning)`.
- RED: 4 failed (formatter bytes TypeError; sqlite3.Warning escapes; formatter RuntimeError escapes handle; `randomblob(4)` query TypeError).
- GREEN: 172 passed. SQLRejeitadoError still propagates unchanged (existing tests `test_rejeitado_nao_e_convertido_em_execucao` stay green). app.py untouched.

## Important 3 (read-only barrier)
- New test `test_execute_readonly_abre_conexao_somente_leitura`: monkeypatches `database.validate_select` to identity, runs an INSERT through `execute_readonly` -> SQLExecucaoError, COUNT unchanged via separate read. Old test kept.
- Mutation check: removing `?mode=ro` from database.py -> "1 failed, 17 passed" (the new test fails); restored -> green.

## Important 4 (docs)
- README.md and CLAUDE.md run blocks now use `pip install -r requirements-dev.txt` with an accurate comment (runtime needs only requirements.txt).

## Minors
- Deleted untracked t10-demo1.png (never committed).
- `DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "edu.db"` in orchestrator.py, used as `build_orchestrator` default (`str | Path` kept). Test checks it is absolute and == project/data/edu.db via inspect.signature, no files created. README/CLAUDE.md updated.
- Mock router regex `\bresolu|\bresolv` (deliberate widening vs. spec §6.2 `resolu`/`resolver`; matches resolva/resolve). Tests: "resolva x² - 5x + 6 = 0", "resolve isso" -> buscar_resolucao; existing precedence tests green. Spec line 108 now mentions the variations.
- Spec §3 and plan "Nota" now say the folder is a git repo (remote origin github Bolodarie/edu-agent-orchestrator).
- Architecture tests: importlib no longer allowed for app.py (`STDLIB - {"importlib"}`), agents/*.py and database.py (added to forbidden sets); new `uses_dynamic_import` detector (`__import__`, `import importlib`, `import_module` names/attributes) with a self-test on violating snippets, and a test asserting none in app.py, database.py, agents/*.py.
- `ensure_ready` uses `BEGIN IMMEDIATE`; test spies on executed statements (`BEGIN IMMEDIATE` present, bare `BEGIN` absent) via a wrapper around sqlite3.connect; idempotency test stays green. (A concurrency-based test was not used because it would not fail deterministically before the change.)
- Mock catalog entry `Logaritmo` (aliases `logaritmo`, `log`); integration test with real MockLLMClient + Database: "exercícios de logaritmo" -> `sem_resultados`, formatter fake never called, SQL contains `LIKE '%Logaritmo%'`, row_count 0. README example list and spec §6.2 sentence updated. Catalog tests for both aliases added.

## Final verification
```
$ .venv/bin/python -m pytest -q
181 passed in 0.28s
$ .venv/bin/python -m pytest -q -W error::DeprecationWarning
181 passed in 0.28s
```
(155 original -> 181: +26 new test cases, pristine output.)

## cwd-independence check
- Started streamlit from /tmp on port 8766 with the absolute app.py path: `/_stcore/health` -> `ok`. Server stopped (it was killed along with my pkill; no process remains).
- Streamlit health does not execute the script, so I additionally ran from /tmp: `python -c "import orchestrator; o = build_orchestrator(); o.handle('exercícios de logaritmo').status"` -> `sem_resultados`; `resolva x² - 5x + 6 = 0` -> BUSCAR_RESOLUCAO. `/tmp/data` does not exist; the project's `data/edu.db` was created and `git check-ignore data/edu.db` confirms it is ignored. `git status` clean.

## Concerns
- None blocking. The `\v` deviation and the `resolv` widening are intentional (documented above). The last-resort `except Exception` in handle() deliberately does not catch BaseException (KeyboardInterrupt etc.).
- The streamlit page itself was not exercised in a browser (only health + build_orchestrator from another cwd), per instruction not to use streamlit.testing.
