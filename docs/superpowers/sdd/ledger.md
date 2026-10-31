# SDD ledger — plan: docs/superpowers/plans/2026-10-31-edu-agent-orchestrator.md

Spec: docs/superpowers/specs/2026-10-31-edu-agent-orchestrator-design.md (reachable, binding authority)
Branch: feat/poc-implementation (from main @ fe80f44). Remote: github-personal:Bolodarie/edu-agent-orchestrator. No push without user OK.
Models: implementers/reviewers = sonnet; final whole-branch review = fable.

## Pre-flight scan (tasks sharing a file or interface; each task vs itself)

| Pair / task | Produces vs consumes | Finding |
|---|---|---|
| T1 -> all | models.py, exceptions.py names | consistent; every later task uses the names defined in T1 |
| T2 -> T4, T9 | validate_latex(text)->(str,list[str]) | consistent |
| T3 -> T4 (same file database.py) | T3 creates database.py (validator); T4 modifies it | consistent; T4 must not overwrite T3 code |
| T3 -> T5 | validate_select imported by a T5 test | consistent (test-only import, allowed) |
| T4 -> T9 | Database(path), ensure_ready(), execute_readonly(sql), schema_description | consistent |
| T5 -> T6,T7,T8 | build_blocks/parse_blocks/LLMClient/MockLLMClient | consistent |
| T6 vs T7 | FakeLLMClient: T6 defines it locally, T7 says "may be moved to tests/fakes.py" | AMBIGUOUS -> Ruling 1 |
| T7 own text | test_envia_intencao_e_schema asserts `INTENCAO: buscar_exercicios` but build_blocks format is `LABEL:` on its own line, content below | AMBIGUOUS -> Ruling 2 |
| T7 -> T9 | generate_sql(pergunta, intent, schema, sql_anterior, erro_anterior)->str | consistent |
| T8 -> T9 | format(intent, rows)->str | consistent |
| T9 own text | tests use Fake agents/LLMs + real Database; test_sem_resultados uses Fake query | consistent once tests/fakes.py exists (Ruling 1) |
| T10 | app/architecture tests; agents/*.py imports ⊆ {llm, models, exceptions} | consistent with T6-T8 imports |
| T1 own text | step 1 says `pip install -r requirements-dev.txt` | conflicts with not touching global Python -> Ruling 3 |
| T1..T10 vs Global Constraints | git: plan has no commit steps, but implementer template commits | consistent: implementers commit (spec/user request: commit everything) |

## Rulings
Ruling: tests/fakes.py is created in Task 6 with FakeLLMClient(respostas: list[str]) exposing .calls: list[tuple[str,str]] and complete(system,user) popping responses in order (repeating the last one when exhausted); Tasks 7-9 import it — avoids three divergent fakes — costs a small rename if a later task needs a different shape.
Ruling: Task 7 prompt assertions use parse_blocks(user) (e.g. parse_blocks(user)["INTENCAO"] == "buscar_exercicios") instead of the literal `INTENCAO: ...` string — matches the build_blocks format defined in Task 5 — none if wrong.
Ruling: dependencies are installed in a project venv (`python3 -m venv --system-site-packages .venv`, then `.venv/bin/pip install pytest`); all commands use `.venv/bin/python -m pytest` — avoids modifying the user's global Python — none if wrong (.venv is gitignored).
Ruling: the SDD artifacts (ledger, briefs, reports) are git-ignored scratch, but the user asked to commit how the flow ran; before deleting the workspace they are copied to docs/superpowers/sdd/ and committed — honors the explicit request — extra files in the repo if wrong.
Note: venv created with 'uv venv --system-site-packages --python 3.10 .venv' (python3 -m venv unavailable); run tests with .venv/bin/python -m pytest
Ruling: user asked (mid-session) to run agents in parallel, max 3 at a time. Skill says never parallel implementers in one checkout; mitigated with one git worktree + branch per parallel task (../edu-agent-orchestrator-wt/tN, branch task/tN-*), merged into feat/poc-implementation by the controller after review. Waves: [T2,T3] -> [T4,T5] -> [T6] -> [T7,T8] -> T9 -> T10 (T6 first because it creates tests/fakes.py used by T7/T8; T5 test imports database from T3). Reviews also count toward the cap of 3 concurrent agents. Dispatched T2/T3 while T1 review was still in flight (T1 is small and isolated) — cost if wrong: T1 fix rework on models/exceptions.
Task 1: minor (deferred): confidence test lacks boundaries 0/1/-0.1 (tests/test_models.py)
Task 1: minor (deferred): no positive-path test for valid status / Intent round-trip from string
Task 1: minor (deferred): Trace.confidence unconstrained while RouterResult.confidence is 0..1 (models.py)
Task 1: minor (deferred): requirements*.txt unpinned (plan-mandated)
Task 1: complete (commits fe80f44..9219287, review clean)
Task 2: implemented (commit d3391b6 on task/t2-latex), review in flight
Task 3: implemented (commit 4b6a663 on task/t3-sql-validator), review in flight
Task 2: review needs fixes — Important: latex_validator.py wrapper uses part.strip(), breaks Markdown when invalid paragraph abuts a fence and drops trailing newline
Task 2: minor (deferred): \left/\right compared by count not order; \\left after escaped backslash; fence info string/longer fences; excerpt cut at 40 chars without ellipsis; missing edge tests (unterminated fence, nested \begin, \{, \leftarrow, empty string, \\$); bare list annotations
Task 2: fix round 1/5 dispatched (resumed implementer), re-review pending
Task 2: fix round 1/5 (1 addressed, 0 open; new Important regression: indented invalid paragraph breaks opening fence at latex_validator.py:101/103; commits d3391b6..ce77a2f)
Task 2: fix round 2/5 dispatched (resumed implementer)
Task 3: review needs fixes — Important: database.py _check_final_limit uses isdigit() (Unicode digits / 5000-digit LIMIT) -> bare ValueError instead of SQLRejeitadoError; no bypass found in security probes
Task 3: minor (deferred): unused sql param in _strip_trailing_semicolon; untyped _Token/list annotations; ch.isspace() treats \xa0/\x0b as whitespace (safe direction); load_extension('x') passes validator (carry to Task 4: keep enable_load_extension disabled); missing tests for lone ';' and IS NOT DISTINCT FROM
Task 3: fix round 1/5 dispatched (resumed implementer)
Task 2: fix round 2/5 re-review in flight (commit 1e03c22)
Task 3: fix round 1/5 done (commit 0b71c15), re-review in flight
Task 3: minor (deferred): zero-padded LIMIT with >18 digits rejected with misleading message (database.py:172)
Task 3: fix round 1/5 (1 addressed, 0 open; commits 4b6a663..0b71c15)
Task 3: complete (commits 9219287..0b71c15, review clean; merged into feat/poc-implementation)
Task 2: minor (deferred): CRLF \r dropped in wrapper trailing whitespace (latex_validator.py:103); out-of-scope: _FENCE treats >=4-space-indented fence as fence
Task 2: fix round 2/5 (1 addressed, 0 open; commits ce77a2f..1e03c22)
Task 2: complete (commits 9219287..1e03c22, review clean; merged into feat/poc-implementation)
Wave B: T4 (worktree t4, branch task/t4-database) and T5 (worktree t5, branch task/t5-llm) based on 15902db (merge of T2+T3)
Task 5: implemented (commit a015cc3 on task/t5-llm), review in flight. Carry to T6/T7: agents must OMIT ERRO_ANTERIOR key on first attempt; seed topic names keep exact accents/casing
Task 4: implemented (commit bf82f64 on task/t4-database), review in flight
Task 4: minor (deferred): database.py unused `Any` import and loose annotations (list, Union) vs brief's list[dict[str, Any]]; deferred BEGIN instead of BEGIN IMMEDIATE in ensure_ready (concurrent first-run only raises busy); ROLLBACK failure could mask original exception; no test exercises the real execute_readonly mode=ro connection (validator blocks writes first); database.py ~480 lines (validator+schema+seed+Database)
Task 4: complete (commits 15902db..bf82f64, review clean; merged into feat/poc-implementation)
Task 5: minor (deferred): mock formatter fragile on malformed DADOS (empty/non-list JSON, NULL renders 'None') llm.py:187-210; bare aliases 'sistema'/'sistemas' broader than 'sistema linear' (llm.py:90-93); 'resolve x'/'resolva' fall to fora_do_escopo (plan-mandated resolu/resolver); 'teste  retry' double space not matched; redundant alias 'fatoracao de polinomios'; invalid/missing INTENCAO silently falls back to BUSCAR_EXERCICIOS in mock
Task 5: complete (commits 15902db..a015cc3, review clean; merged into feat/poc-implementation)
Task 6: implemented (commit a1df1bd on feat), review in flight
Wave D: T7 (worktree t7) and T8 (worktree t8) dispatched from a1df1bd in parallel with T6 review (cost if wrong: rebase if T6 review changes tests/fakes.py)
Task 6: minor (deferred): router.py:61 pydantic lax mode accepts confidence true / "0.5" (use strict or reject bool); router.py:62 RecursionError from pathological JSON not caught; prose before a fence not handled (acceptable, non-recoverable); no tests for bool/string confidence
Task 6: complete (commits 3a3e492..a1df1bd, review clean; on feat/poc-implementation; tests/fakes.py unchanged so T7/T8 need no rebase)
Task 7: implemented (commit 151a0a1 on task/t7-query), review in flight
Task 8: implemented (commit f86bb97 on task/t8-formatter), review in flight
Task 7: review needs fixes — Important: _FENCE_RE/_strip_fences duplicated verbatim between agents/query.py and agents/router.py
Task 7: minor (deferred): fence stripping only handles output that is entirely one fence (prose + fenced block / stray trailing fence passes through; validator rejects -> costs a retry); no tests for lowercase select / 'selected' / whitespace-only output
Ruling: fix for Task 7 moves the helper to llm.strip_code_fences (public, behavior unchanged) and edits agents/router.py (Task 6 file) — it is the only home allowed by the import rules (agents may import llm) and removes the duplication — cost if wrong: Task 7 diff now also touches router.py/llm.py
Task 7: fix round 1/5 dispatched (resumed implementer)
Task 8: minor (deferred): formatter.py:44 non-JSON-native row values (Decimal/date/bytes) raise bare TypeError (brief mandates json.dumps; could add default=str); no test asserts SYSTEM_PROMPT is passed or that empty rows still sends DADOS
Task 8: complete (commits a1df1bd..f86bb97, review clean; merged into feat/poc-implementation)
Task 7: fix round 1/5 done (commit af41bcb), re-review in flight
Task 7: fix round 1/5 (1 addressed, 0 open; commits 151a0a1..af41bcb)
Task 7: complete (commits a1df1bd..af41bcb, review clean; merged into feat/poc-implementation)
Task 9: implemented (commit d060a34 on feat), review in flight
Task 9 note: trace.avisos also carries technical error detail for router/formatter failures (no dedicated trace field) — decide at review
Task 10: dispatched in worktree t10 (branch task/t10-app from d060a34) in parallel with T9 review (cost if wrong: rebase if T9 review changes the orchestrator interface)
Task 9: minor (deferred): trace.avisos carries technical error detail for router/formatter failures (acceptable per spec; a dedicated Trace.erro field could come later); non-AgentPipelineError exceptions escape handle() by design (a real LLM client must wrap transport errors in an AgentPipelineError subclass); after a generation failure the next attempt gets an empty SQL_ANTERIOR block (could keep last non-empty SQL); max_attempts<1 not validated (orchestrator.py:44); non-recoverable query error recorded twice (attempts + avisos); test_resumo_e_resolucao has unused `coluna` and in-test branching (tests/test_orchestrator.py:56-66)
Task 9: complete (commits b4629c2..d060a34, review clean; on feat/poc-implementation)
Task 10: implemented (commits 94bb346, dce42f8 on task/t10-app), review in flight
Task 10: minor (deferred): architecture test blind to dynamic imports (importlib/__import__) and relative imports; app.py appends user message to session_state before handle() runs (orphan turn if an unexpected exception escapes); README 'como rodar' block lacks `pip install -r requirements-dev.txt` before pytest; page_icon emoji; spinner text 'Pensando...' beyond the brief
Task 10: complete (commits d060a34..dce42f8, review clean; merged into feat/poc-implementation)
All 10 tasks complete. Final whole-branch review next (MERGE_BASE = fe80f44).
Final review (fable): Ready to merge = WITH FIXES. Important: (1) validator tokenizer uses ch.isspace() -> NBSP/\x85 etc. bypass LIMIT cap and \x00 escapes as bare ValueError (database.py:54); (2) non-AgentPipelineError escapes handle() (formatter json.dumps TypeError on bytes; NUL ValueError; sqlite3.Warning not a sqlite3.Error); (3) read-only barrier test does not exercise execute_readonly (tests/test_database.py:91-98); (4) README/CLAUDE.md run block lacks requirements-dev.txt (fresh clone: pytest not found).
Ruling: final-review fix wave is ONE dispatch to a single implementer covering Important 1-4 plus these cheap minors from the review: delete untracked t10-demo1.png, anchor default DB path to the module dir, \bresolv regex, stale 'não é repositório git' lines in spec/plan, importlib/__import__ hardening in the architecture test, BEGIN IMMEDIATE in ensure_ready, add a no-row catalog topic ('Logaritmo') so sem_resultados has a demo path (spec §6.2). Remaining deferred minors stay deferred (triaged 'can stay' by the final reviewer). Cost if wrong: slightly larger fix diff than strictly required.
Final review: fix wave dispatched (FIX_BASE=0b875da)
Final review: fix wave done (commits 08cfa35, 50f0aa5, 8d3618f, 5931025), scoped re-review in flight. Note: spec §6.2 precedence line still says resolu/resolver (widened to resolv in code; recorded at spec line ~108)
Final review: scoped re-review clean — all 4 Important + cheap minors addressed (commits 08cfa35..5931025). Minor (deferred): NUL inside a string literal accepted by validator, sqlite raises bare ValueError (contained by handle() catch-all, not retried); formatter mock renders empty $$ for blob columns (cosmetic)
All tasks + final review complete.
