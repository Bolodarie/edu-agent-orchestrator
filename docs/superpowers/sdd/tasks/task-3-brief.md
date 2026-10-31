### Task 3: Validador de SQL (`database.py`, parte 1)

**Files:**
- Create: `database.py` (somente a parte do validador neste task), `tests/test_sql_validator.py`

**Interfaces:**
- Consumes: `SQLRejeitadoError` (Task 1).
- Produces: `ALLOWED_TABLES: frozenset[str]` = `{"Topicos_Algebra","Exercicios","Resolucoes"}`; `MAX_LIMIT = 50`; `validate_select(sql: str, allowed_tables: frozenset[str] = ALLOWED_TABLES, max_limit: int = MAX_LIMIT) -> str` — devolve o SQL sem o `;` final ou levanta `SQLRejeitadoError`.

Regras (spec §6.4): tokenizar respeitando literais `'...'` (com `''` escapado); rejeitar comentários `--` e `/* */` fora de literais; rejeitar mais de uma instrução (um `;` final é tolerado); primeira palavra `SELECT`, `WITH` rejeitado, subconsultas aceitas; palavras proibidas fora de literais (`INSERT UPDATE DELETE DROP ALTER CREATE ATTACH DETACH PRAGMA REPLACE VACUUM`); todo identificador após `FROM`/`JOIN` deve estar na lista (aliases aceitos); `LIMIT <inteiro>` obrigatório como cláusula final do nível superior, `≤ max_limit`.

- [ ] **Step 1: Write the failing tests** (`tests/test_sql_validator.py`):
  - Aceitos (devolvem string): `"SELECT t.nome FROM Topicos_Algebra t LIMIT 3"`; com `;` final; com JOIN e alias (`Exercicios e JOIN Topicos_Algebra t ON e.topico_id = t.id LIMIT 5`); `WHERE t.nome LIKE '%2º Grau%' LIMIT 5`; literal contendo `;` e `drop` (`WHERE t.nome LIKE '%drop; x%' LIMIT 5`); `LIMIT 50`.
  - Rejeitados com `SQLRejeitadoError` (parametrizar): `DROP TABLE Exercicios`; `SELECT 1; DROP TABLE Exercicios LIMIT 1`; `SELECT * FROM Usuarios LIMIT 1`; `SELECT * FROM Exercicios` (sem LIMIT); `SELECT * FROM Exercicios LIMIT 51`; `SELECT * FROM Exercicios LIMIT 5 -- x`; `SELECT * FROM Exercicios /* x */ LIMIT 5`; `WITH x AS (SELECT 1) SELECT * FROM x LIMIT 1`; `SELECT * FROM Exercicios WHERE id IN (SELECT id FROM Usuarios) LIMIT 5`; `SELECT * FROM Exercicios LIMIT 5; DELETE FROM Exercicios`; string vazia.
- [ ] **Step 2:** `pytest tests/test_sql_validator.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar `validate_select` em `database.py` (tokenizador à mão, sem regex único gigante; identificadores comparados sem diferenciar maiúsculas, mas a lista usa a grafia canônica).
- [ ] **Step 4:** `pytest tests/test_sql_validator.py -v`. Esperado: todos PASS.

---

