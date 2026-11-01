### Task 2: `latex_validator.py`

**Files:**
- Create: `latex_validator.py`, `tests/test_latex_validator.py`

**Interfaces:**
- Produces: `validate_latex(text: str) -> tuple[str, list[str]]` — devolve o texto saneado e a lista de avisos (um por parágrafo embrulhado).

Regras (spec §6.5): ignora blocos de código com cercas ` ``` `; `\$` conta como cifrão literal; unidade é o parágrafo (separado por linha em branco); parágrafo com `$`/`$$` sem par, `{}` desbalanceadas, ou `\left/\right` e `\begin/\end` sem par é embrulhado inteiro em bloco de código. Um aviso em português por parágrafo embrulhado.

- [ ] **Step 1: Write the failing tests** (`tests/test_latex_validator.py`):
  - `test_valido_passa_intacto`: `"Resolva $x^2=4$.\n\n$$\\frac{a}{b}$$"` → texto igual, avisos `[]`.
  - `test_dolar_sem_par`: `"Valor $x+1"` → texto contém "```" e `Valor $x+1`; `len(avisos) == 1`.
  - `test_chaves_desbalanceadas`: `"$\\frac{a}{b$"` → embrulhado, 1 aviso.
  - `test_begin_end_sem_par`: `"$$\\begin{aligned} x=1 $$"` → embrulhado.
  - `test_left_right_sem_par`: `"$\\left( x $"` → embrulhado.
  - `test_cifrao_escapado_nao_conta`: `"Custa \\$5 hoje"` → intacto, sem avisos.
  - `test_bloco_duplo_multilinha_no_mesmo_paragrafo`: `"$$\n\\begin{aligned}\nx&=1\\\\\ny&=2\n\\end{aligned}\n$$"` → intacto, sem avisos.
  - `test_bloco_de_codigo_e_ignorado`: texto com cerca contendo `$` solto → intacto.
  - `test_so_o_paragrafo_ruim_e_embrulhado`: dois parágrafos, um válido e um inválido → o válido continua fora de cerca; 1 aviso.
- [ ] **Step 2:** `pytest tests/test_latex_validator.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `validate_latex`. Abordagem: separar o texto em segmentos dentro/fora de cercas, depois em parágrafos por `\n\s*\n`; para cada parágrafo, remover `\$`, contar `$$` e `$` restantes (paridade), checar balanço de chaves ignorando `\{`/`\}`, e parear `\left/\right` e `\begin{x}/\end{x}`.
- [ ] **Step 4:** `pytest tests/test_latex_validator.py -v`. Esperado: 9 PASS.

---

