### Task 10: `app.py`, teste de fronteiras e README

**Files:**
- Create: `app.py`, `tests/test_architecture.py`, `README.md`

**Interfaces:**
- Consumes: `build_orchestrator`, `Orchestrator.handle` (Task 9); `OrchestratorResponse`, `Trace` (Task 1).

`app.py` (spec §4.9): `st.chat_input`, `st.chat_message`; histórico em `st.session_state`; orquestrador via `@st.cache_resource` chamando `build_orchestrator()`; resposta renderizada com `st.markdown`; `status` escolhe estilo (`ok` normal, `fora_do_escopo`/`sem_resultados` → `st.info`/`st.warning`, `erro` → `st.error`); `trace` em `st.expander("Como a resposta foi gerada")` com intenção e confiança, cada tentativa de SQL com erro e linhas, avisos e tempos. Cada mensagem do histórico guarda o `OrchestratorResponse` para redesenhar, sem reexecutar o pipeline.

`README.md`: propósito, diagrama das camadas (ASCII ou mermaid), como rodar, como trocar o mock por LLM real (nova classe + linha em `build_orchestrator()`), exemplos de perguntas (incluindo "teste retry"), limite conhecido de não ter memória de conversa e o retry citado.

- [ ] **Step 1: Write the failing test** (`tests/test_architecture.py`, usa `ast` para ler imports de cada arquivo):
  - `test_app_importa_so_orchestrator_e_models`: módulos de `app.py` ⊆ {`streamlit`, `orchestrator`, `models`} (stdlib permitida).
  - `test_agents_nao_importam_database`: nenhum arquivo em `agents/` importa `database`, `orchestrator` ou `app`.
  - `test_database_nao_importa_agentes_nem_llm`: `database.py` não importa `agents`, `llm`, `orchestrator`, `app`.
  - `test_agents_so_dependem_do_permitido`: imports internos de `agents/*.py` ⊆ {`llm`, `models`, `exceptions`}.
  - Comprovar que o teste detecta violação: função auxiliar `imports_of(source: str) -> set[str]` testada com um trecho de código com `import database` (retorna `{"database"}`).
- [ ] **Step 2:** `pytest tests/test_architecture.py -v`. Esperado: FAIL (`app.py` inexistente).
- [ ] **Step 3:** Implementar `app.py` e escrever `README.md`.
- [ ] **Step 4:** `pytest -v`. Esperado: suíte inteira PASS.
- [ ] **Step 5 (demo):** `streamlit run app.py --server.headless true` em segundo plano; `curl -s localhost:8501/_stcore/health` devolve `ok`; parar o servidor. Depois, com `AppTest` descartado (fora de escopo), verificar manualmente no navegador (ou pedir ao usuário): uma pergunta de exercícios renderiza LaTeX, "teste retry exercícios de fatoração" mostra 2 tentativas no expander, "capital da França" mostra a mensagem de fora de escopo.
