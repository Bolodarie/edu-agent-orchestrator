### Task 6: `agents/router.py`

**Files:**
- Create: `agents/router.py`, `tests/test_agent_router.py`

**Interfaces:**
- Consumes: `LLMClient`, `build_blocks` (Task 5); `Intent`, `RouterResult`; `IntencaoDesconhecidaError`.
- Produces: `class RouterAgent` com `__init__(self, llm: LLMClient)` e `classify(self, pergunta: str) -> RouterResult`.

Monta system prompt (constante) listando as intenções válidas e exigindo JSON `{"intent","confidence"}`; user = `build_blocks(PERGUNTA=pergunta)`. Remove cercas ` ``` ` antes do `json.loads`.

- [ ] **Step 1: Write the failing tests** com um `FakeLLMClient` local (classe com `respostas: list[str]` e `calls: list[tuple[str,str]]`):
  - `test_classifica_json_valido`: resposta `{"intent":"buscar_resumo","confidence":0.8}` → `RouterResult(intent=Intent.BUSCAR_RESUMO, confidence=0.8)`.
  - `test_aceita_json_em_cerca`: resposta embrulhada em ```` ```json ````.
  - `test_json_malformado`: `"não sei"` → `IntencaoDesconhecidaError`.
  - `test_intencao_fora_do_enum`: `{"intent":"apagar_tudo","confidence":1}` → `IntencaoDesconhecidaError`.
  - `test_confianca_invalida`: `confidence: 7` → `IntencaoDesconhecidaError` (converter `ValidationError`).
  - `test_envia_pergunta_no_prompt`: o `user` recebido contém `PERGUNTA:` e o texto.
- [ ] **Step 2:** `pytest tests/test_agent_router.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `RouterAgent`.
- [ ] **Step 4:** `pytest tests/test_agent_router.py -v`. Esperado: 6 PASS.

---

