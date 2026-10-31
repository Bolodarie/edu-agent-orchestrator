### Task 4: Schema, seed e execução somente leitura (`database.py`, parte 2)

**Files:**
- Modify: `database.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: `validate_select`, `SQLExecucaoError`, `SQLRejeitadoError`, `validate_latex` (só nos testes).
- Produces: `SCHEMA_DESCRIPTION: str` (texto com as 3 tabelas e colunas, usado no prompt da consulta); `class Database` com `__init__(self, path: str | Path)`, `ensure_ready(self) -> None` (cria diretório e arquivo, schema e seed se o arquivo não existir), `execute_readonly(self, sql: str) -> list[dict[str, Any]]`, atributo `schema_description: str`.

Schema (spec §4.7): `Topicos_Algebra(id, nome, descricao, resumo_teorico)`, `Exercicios(id, topico_id → Topicos_Algebra, enunciado_latex, dificuldade)`, `Resolucoes(id, exercicio_id → Exercicios, passo_a_passo_latex)`. Seed conforme "Decisões do plano". `execute_readonly` chama `validate_select`, abre `file:{path}?mode=ro` com `uri=True`, `row_factory` para dict, e converte `sqlite3.Error` em `SQLExecucaoError`.

- [ ] **Step 1: Write the failing tests** (`tests/test_database.py`, fixture `db` com `tmp_path / "edu.db"` e `ensure_ready()`):
  - `test_ensure_ready_cria_arquivo_e_popula`: arquivo existe; contagem de tópicos == 4; cada tópico tem entre 2 e 3 exercícios; cada exercício tem exatamente 1 resolução (consultas via `execute_readonly` com `LIMIT 50`).
  - `test_ensure_ready_e_idempotente`: chamar duas vezes não duplica linhas.
  - `test_execute_readonly_devolve_dicts`: `SELECT nome FROM Topicos_Algebra LIMIT 1` → lista de 1 dict com chave `nome`.
  - `test_sql_invalido_levanta_rejeitado`: `DROP TABLE Exercicios` → `SQLRejeitadoError`.
  - `test_erro_do_sqlite_vira_execucao`: `SELECT coluna_inexistente FROM Exercicios LIMIT 1` → `SQLExecucaoError`.
  - `test_conexao_e_somente_leitura`: abrir diretamente `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` e tentar `INSERT` levanta `sqlite3.OperationalError` (prova a segunda barreira, independente do validador).
  - `test_seed_latex_e_valido`: para cada `enunciado_latex`/`passo_a_passo_latex`, `validate_latex(f"$$\n{x}\n$$")` não gera avisos; para cada `resumo_teorico`, `validate_latex(x)` não gera avisos.
- [ ] **Step 2:** `pytest tests/test_database.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implementar schema, seed e `Database` em `database.py`. Seed escrito como constantes de dados no topo ou fim do arquivo; conexão de escrita só dentro de `ensure_ready`.
- [ ] **Step 4:** `pytest tests/test_database.py tests/test_sql_validator.py -v`. Esperado: todos PASS.

---

