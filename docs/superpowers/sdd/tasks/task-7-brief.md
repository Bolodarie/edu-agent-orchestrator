### Task 7: `agents/query.py`

**Files:**
- Create: `agents/query.py`, `tests/test_agent_query.py`

**Interfaces:**
- Consumes: `LLMClient`, `build_blocks`; `Intent`; `SaidaDoAgenteInvalidaError`.
- Produces: `class QueryAgent` com `__init__(self, llm: LLMClient)` e `generate_sql(self, pergunta: str, intent: Intent, schema: str, sql_anterior: str | None = None, erro_anterior: str | None = None) -> str`.

User = `build_blocks(PERGUNTA=..., INTENCAO=intent.value, SCHEMA=schema)` e, só quando ambos `sql_anterior` e `erro_anterior` forem dados, `SQL_ANTERIOR=...` e `ERRO_ANTERIOR=...`. Remove cercas de código da saída e espaços; vazio ou sem a palavra `SELECT` (case-insensitive) → `SaidaDoAgenteInvalidaError`. O agente **não** importa `database`.

- [ ] **Step 1: Write the failing tests** (`FakeLLMClient` como na Task 6; pode ser movido para `tests/fakes.py` e reutilizado):
  - `test_devolve_sql_limpo`: resposta com cercas ```` ```sql\nSELECT 1 LIMIT 1\n``` ```` → `"SELECT 1 LIMIT 1"`.
  - `test_saida_vazia`: `""` e `"```\n```"` → `SaidaDoAgenteInvalidaError`.
  - `test_saida_em_prosa`: `"Claro! Aqui está sua consulta."` → `SaidaDoAgenteInvalidaError`.
  - `test_primeira_tentativa_nao_envia_bloco_de_erro`: o prompt não contém `ERRO_ANTERIOR:`.
  - `test_correcao_envia_sql_e_erro`: com `sql_anterior="SELECT 1"` e `erro_anterior="sem LIMIT"`, o prompt contém `SQL_ANTERIOR:`, `ERRO_ANTERIOR:` e ambos os textos.
  - `test_envia_intencao_e_schema`: prompt contém `INTENCAO: buscar_exercicios` (ou o bloco equivalente em `parse_blocks`) e o schema.
- [ ] **Step 2:** `pytest tests/test_agent_query.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `QueryAgent`.
- [ ] **Step 4:** `pytest tests/test_agent_query.py -v`. Esperado: 6 PASS.

---

