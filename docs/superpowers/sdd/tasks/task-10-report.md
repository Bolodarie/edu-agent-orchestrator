# Task 10 report: app.py, tests/test_architecture.py, README.md

Status: DONE
Worktree: /home/igorg/facul/aprendizado/edu-agent-orchestrator-wt/t10 (branch task/t10-app, base d060a34)

## Commits
- 94bb346 feat: add Streamlit app and architecture boundary tests
- dce42f8 docs: add README with layer diagram and usage
(no Claude/AI attribution, no Co-Authored-By)

## Implementation
- app.py: imports only `streamlit`, `models.OrchestratorResponse`, `orchestrator.{Orchestrator, build_orchestrator}`. `get_orchestrator()` is `@st.cache_resource` -> `build_orchestrator()`. `st.session_state.messages` holds `{"role":"user","text"}` / `{"role":"assistant","response": OrchestratorResponse}`; redraw uses the stored response, never re-runs the pipeline. Status style: ok -> st.markdown; fora_do_escopo -> st.info; sem_resultados -> st.warning; erro -> st.error. Trace in `st.expander("Como a resposta foi gerada")`: intent + confidence, each SQL attempt (code block, error, row_count), avisos, tempos_ms. All UI text pt-BR. Module ends with `main()` call (Streamlit script style).
- tests/test_architecture.py: `imports_of(source) -> set[str]` using `ast` (handles `import x`, `import x.y`, `from x import y`, nested imports; ignores relative imports); own test proves detection (`import database` -> {"database"}). Tests: app imports subset of {streamlit, orchestrator, models} + stdlib (`sys.stdlib_module_names`); agents/*.py do not import database/orchestrator/app; database.py does not import agents/llm/orchestrator/app; agents' internal (project-module) imports subset of {llm, models, exceptions}. "Internal" = .py files/packages in repo root, so third-party `pydantic` in router.py is not flagged (per "internos").
- README.md (pt-BR): purpose, ASCII + mermaid diagram, dependency rule, retry (3 attempts), how to run, example questions incl. "teste retry", swapping mock for real LLM (new class implementing LLMClient + one line in build_orchestrator), known limit (no conversation memory; contract would become `handle(texto, historico)`).

## TDD evidence
RED (before app.py existed):
`.venv/bin/python -m pytest tests/test_architecture.py -v`
-> `FileNotFoundError: .../t10/app.py` ; `FAILED tests/test_architecture.py::test_app_importa_so_orchestrator_e_models` ; `1 failed, 4 passed` (the other 4 are legitimately satisfied by existing code; only the app test depends on app.py).
GREEN (after app.py): `pytest -v` -> `155 passed in 0.30s` (final run after README: 155 passed in 0.23s).

## Demo verification (Step 5)
- `.venv/bin/python -m streamlit run app.py --server.headless true --server.port 8765` in background from worktree; `curl -s localhost:8765/_stcore/health` -> `ok`. Server stopped afterwards (curl later returns nothing; no streamlit process left).
- A real browser check WAS done with the Playwright MCP tool against localhost:8765:
  - "exercícios de equação do 2º grau": 3 exercises rendered, `.katex` elements = 3 (LaTeX renders).
  - "teste retry exercícios de fatoração": expander shows intent buscar_exercicios (confiança 90%), Tentativa 1 `SELECT * FROM Exercicios` with "Erro: SQL rejeitado: a consulta deve terminar com LIMIT <inteiro>", Tentativa 2 with the JOIN SQL, "Linhas devolvidas: 3", tempos (roteador, consulta, banco, formatador, latex). Earlier messages were redrawn from session state on rerun.
  - "capital da França": st.info alert with the MSG_FORA_DO_ESCOPO text; no st exception elements on the page.
- Also confirmed via build_orchestrator: "resumo de fatoração" -> ok/buscar_resumo, "resolução de sistema linear" -> ok/buscar_resolucao (README examples are valid).
- Only visual caveat: material-icon names ("face", "smart_toy") appear as text in innerText extraction (icon font ligatures), not a bug.

## Files changed
app.py, tests/test_architecture.py, README.md (all new). data/edu.db created by the demo in worktree is gitignored; git status clean after commits.

## Self-review / concerns
- None blocking. `page_icon="📐"` is an emoji in the UI (user-visible, harmless; remove if emoji-free is wanted).
- `main()` runs at import, so app.py cannot be imported in tests without side effects; the architecture test reads it via ast only (by design).
- Spinner text "Pensando..." is the only extra UI text beyond the brief.
