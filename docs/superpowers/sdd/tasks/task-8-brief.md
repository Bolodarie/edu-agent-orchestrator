### Task 8: `agents/formatter.py`

**Files:**
- Create: `agents/formatter.py`, `tests/test_agent_formatter.py`

**Interfaces:**
- Consumes: `LLMClient`, `build_blocks`; `Intent`.
- Produces: `class FormatterAgent` com `__init__(self, llm: LLMClient)` e `format(self, intent: Intent, rows: list[dict[str, Any]]) -> str`.

User = `build_blocks(INTENCAO=intent.value, DADOS=json.dumps(rows, ensure_ascii=False))`; devolve a saída do LLM sem alterá-la (a validação de LaTeX é do orquestrador).

- [ ] **Step 1: Write the failing tests:**
  - `test_serializa_linhas_em_json`: o `user` enviado contém `DADOS:` e `parse_blocks` + `json.loads` recuperam as linhas originais, incluindo acentos.
  - `test_devolve_saida_do_llm_intacta`: `FakeLLMClient` com `"$$ x $$"` → o mesmo texto.
  - `test_nao_valida_latex`: saída com `$` solto não gera erro nem altera o texto.
  - Integração com mock: `FormatterAgent(MockLLMClient()).format(Intent.BUSCAR_RESUMO, [{"nome":"Fatoração","resumo_teorico":"Texto $a^2$"}])` contém `Texto $a^2$`.
- [ ] **Step 2:** `pytest tests/test_agent_formatter.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `FormatterAgent`.
- [ ] **Step 4:** `pytest tests/test_agent_formatter.py -v`. Esperado: 4 PASS.

---

