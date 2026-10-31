### Task 9: `orchestrator.py`

**Files:**
- Create: `orchestrator.py`, `tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `RouterAgent.classify`, `QueryAgent.generate_sql`, `FormatterAgent.format`, `Database.execute_readonly`/`.schema_description`/`.ensure_ready`, `validate_latex`, todos os modelos e exceções.
- Produces: `class Orchestrator` com `__init__(self, router: RouterAgent, query_agent: QueryAgent, formatter: FormatterAgent, database: Database, max_attempts: int = 3)` e `handle(self, texto: str) -> OrchestratorResponse`; `build_orchestrator(db_path: str | Path = "data/edu.db") -> Orchestrator` (monta `MockLLMClient`, três agentes, `Database`, chama `ensure_ready()`).

Fluxo (spec §4.3): texto vazio/só espaços → `fora_do_escopo` sem chamar nada. Roteador → `FORA_DO_ESCOPO` → status `fora_do_escopo`. Laço de até `max_attempts`: gerar SQL (passando `sql_anterior`/`erro_anterior` a partir da 2ª), executar; erro recuperável é registrado em `trace.attempts` (com `error`) e leva à próxima tentativa; erro não recuperável sai do laço. Esgotado → `erro`. Zero linhas → `sem_resultados`. Senão formatar, `validate_latex`, `ok`. `trace` registra intenção, confiança, tentativas (com `row_count`), avisos de LaTeX e `tempos_ms` com as chaves `roteador`, `consulta`, `banco`, `formatador`, `latex` (as que ocorreram). Qualquer `AgentPipelineError` não tratada vira `erro` com mensagem amigável; o detalhe técnico fica em `trace`. Mensagens ao aluno por status em português (constantes do módulo).

- [ ] **Step 1: Write the failing tests** (`tests/test_orchestrator.py`; fixture `db` real em `tmp_path`; agentes reais sobre `MockLLMClient` salvo onde indicado; usar `FakeLLMClient` em `tests/fakes.py` para forçar saídas):
  - `test_fluxo_feliz`: `handle("exercícios de equação do 2º grau")` → `status == "ok"`; texto contém um enunciado real do banco; `trace.intent == Intent.BUSCAR_EXERCICIOS`; `len(trace.attempts) == 1` com `row_count > 0`; `tempos_ms` tem `roteador`, `consulta`, `banco`, `formatador`.
  - `test_resumo_e_resolucao`: "resumo de fatoração" e "resolução de sistemas lineares" → `ok` com conteúdo dos respectivos dados.
  - `test_fora_do_escopo`: "qual a capital da França" → `fora_do_escopo`, `trace.attempts == []`.
  - `test_retry_com_gancho`: "teste retry exercícios de fatoração" → `ok`; `len(trace.attempts) == 2`; a 1ª com `error` preenchido, a 2ª com `error is None`.
  - `test_esgota_tentativas`: `QueryAgent` com Fake que sempre devolve `SELECT * FROM Exercicios` → `status == "erro"`; `len(trace.attempts) == 3`; `max_attempts=2` configurável.
  - `test_saida_invalida_do_agente_conta_como_tentativa`: Fake devolve prosa e depois SQL válido → `ok` com 2 tentativas, a 1ª com `sql == ""`.
  - `test_sem_resultados`: pergunta com tópico que o mock filtra sem linhas (ex.: usar Fake de consulta com `WHERE t.nome LIKE '%inexistente%' LIMIT 5`) → `sem_resultados`; o formatador não é chamado.
  - `test_erro_nao_recuperavel`: Fake de roteador com JSON inválido → `status == "erro"`, sem consultas.
  - `test_entrada_vazia` (Review Focus 1): `""` e `"   \n"` → `fora_do_escopo`; um Fake que registra chamadas confirma 0 chamadas ao LLM e ao banco.
  - `test_latex_invalido_vira_aviso`: formatador Fake devolve `"$ x"` → `status == "ok"`, texto com cerca de código, `trace.avisos` com 1 item.
  - `test_build_orchestrator`: `build_orchestrator(tmp_path / "edu.db")` cria o arquivo e responde `ok` a "exercícios de fatoração".
- [ ] **Step 2:** `pytest tests/test_orchestrator.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `Orchestrator` e `build_orchestrator`. Tempo medido com `time.perf_counter`.
- [ ] **Step 4:** `pytest tests/test_orchestrator.py -v`. Esperado: 11 PASS.

---

