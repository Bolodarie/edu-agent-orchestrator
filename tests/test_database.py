import sqlite3

import pytest

import database
from database import SCHEMA_DESCRIPTION, Database
from exceptions import SQLExecucaoError, SQLRejeitadoError
from latex_validator import validate_latex


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "edu.db")
    database.ensure_ready()
    return database


def test_ensure_ready_cria_arquivo_e_popula(db, tmp_path):
    assert (tmp_path / "edu.db").exists()

    topicos = db.execute_readonly("SELECT id, nome FROM Topicos_Algebra LIMIT 50")
    assert len(topicos) == 4
    assert {t["nome"] for t in topicos} == {
        "Equação do 1º Grau",
        "Equação do 2º Grau",
        "Sistemas Lineares",
        "Fatoração",
    }

    for topico in topicos:
        exercicios = db.execute_readonly(
            f"SELECT id FROM Exercicios WHERE topico_id = {topico['id']} LIMIT 50"
        )
        assert 2 <= len(exercicios) <= 3
        for exercicio in exercicios:
            resolucoes = db.execute_readonly(
                "SELECT id FROM Resolucoes "
                f"WHERE exercicio_id = {exercicio['id']} LIMIT 50"
            )
            assert len(resolucoes) == 1


def test_dificuldades_do_seed(db):
    linhas = db.execute_readonly("SELECT DISTINCT dificuldade FROM Exercicios LIMIT 50")
    assert {l["dificuldade"] for l in linhas} <= {"fácil", "média", "difícil"}


def test_ensure_ready_cria_diretorio_pai(tmp_path):
    caminho = tmp_path / "data" / "sub" / "edu.db"
    Database(caminho).ensure_ready()
    assert caminho.exists()


def test_ensure_ready_e_idempotente(db):
    antes = {
        tabela: len(db.execute_readonly(f"SELECT id FROM {tabela} LIMIT 50"))
        for tabela in ("Topicos_Algebra", "Exercicios", "Resolucoes")
    }
    db.ensure_ready()
    db.ensure_ready()
    depois = {
        tabela: len(db.execute_readonly(f"SELECT id FROM {tabela} LIMIT 50"))
        for tabela in ("Topicos_Algebra", "Exercicios", "Resolucoes")
    }
    assert antes == depois
    assert antes["Topicos_Algebra"] == 4


def test_execute_readonly_devolve_dicts(db):
    linhas = db.execute_readonly("SELECT nome FROM Topicos_Algebra LIMIT 1")
    assert len(linhas) == 1
    assert isinstance(linhas[0], dict)
    assert "nome" in linhas[0]


def test_sql_invalido_levanta_rejeitado(db):
    with pytest.raises(SQLRejeitadoError):
        db.execute_readonly("DROP TABLE Exercicios")


def test_erro_do_sqlite_vira_execucao(db):
    with pytest.raises(SQLExecucaoError):
        db.execute_readonly("SELECT coluna_inexistente FROM Exercicios LIMIT 1")


def test_rejeitado_nao_e_convertido_em_execucao(db):
    with pytest.raises(SQLRejeitadoError) as info:
        db.execute_readonly("SELECT * FROM Exercicios")
    assert not isinstance(info.value, SQLExecucaoError)


def test_conexao_e_somente_leitura(db, tmp_path):
    caminho = tmp_path / "edu.db"
    conexao = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conexao.execute("INSERT INTO Topicos_Algebra (nome) VALUES ('x')")
    finally:
        conexao.close()


def test_carregamento_de_extensao_nao_esta_habilitado(db):
    # O validador deixa passar load_extension(...); a barreira é a conexão,
    # que nunca habilita o carregamento de extensões.
    with pytest.raises(SQLExecucaoError):
        db.execute_readonly("SELECT load_extension('nao_existe') FROM Exercicios LIMIT 1")


def test_banco_inexistente_vira_execucao(tmp_path):
    with pytest.raises(SQLExecucaoError):
        Database(tmp_path / "nao_criado.db").execute_readonly(
            "SELECT * FROM Exercicios LIMIT 1"
        )


def test_schema_description_menciona_tabelas_e_colunas(db):
    assert db.schema_description == SCHEMA_DESCRIPTION
    for trecho in (
        "Topicos_Algebra", "Exercicios", "Resolucoes",
        "resumo_teorico", "enunciado_latex", "dificuldade",
        "passo_a_passo_latex", "topico_id", "exercicio_id",
    ):
        assert trecho in SCHEMA_DESCRIPTION


def test_seed_latex_e_valido(db):
    colunas_matematicas = [
        ("Exercicios", "enunciado_latex"),
        ("Resolucoes", "passo_a_passo_latex"),
    ]
    for tabela, coluna in colunas_matematicas:
        linhas = db.execute_readonly(f"SELECT {coluna} FROM {tabela} LIMIT 50")
        assert linhas
        for linha in linhas:
            valor = linha[coluna]
            assert "$" not in valor
            assert "\n\n" not in valor
            _, avisos = validate_latex(f"$$\n{valor}\n$$")
            assert avisos == [], valor

    resumos = db.execute_readonly("SELECT resumo_teorico FROM Topicos_Algebra LIMIT 50")
    assert resumos
    for linha in resumos:
        _, avisos = validate_latex(linha["resumo_teorico"])
        assert avisos == [], linha["resumo_teorico"]


def test_resolucoes_do_seed_quebram_linhas_com_barra_dupla(db):
    linhas = db.execute_readonly("SELECT passo_a_passo_latex FROM Resolucoes LIMIT 50")
    for linha in linhas:
        valor = linha["passo_a_passo_latex"]
        for trecho in valor.split("\n")[1:-2]:
            assert trecho.endswith("\\\\"), valor


@pytest.mark.parametrize("sql", [
    "SELECT * FROM Exercicios LIMIT\xa05",
    "SELECT * FROM Exercicios\x00 LIMIT 5",
])
def test_execute_readonly_rejeita_caracteres_que_o_sqlite_interpreta_diferente(db, sql):
    with pytest.raises(SQLRejeitadoError):
        db.execute_readonly(sql)


def test_sqlite_warning_vira_execucao(db, monkeypatch):
    # No Python 3.10, sqlite3.Warning não herda de sqlite3.Error.
    class _Conexao:
        row_factory = None

        def execute(self, sql):
            raise sqlite3.Warning("You can only execute one statement at a time.")

        def close(self):
            pass

    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: _Conexao())
    with pytest.raises(SQLExecucaoError):
        db.execute_readonly("SELECT * FROM Exercicios LIMIT 1")


def test_execute_readonly_abre_conexao_somente_leitura(db, monkeypatch):
    # Sem o validador no caminho, só a URI `mode=ro` de execute_readonly barra a escrita.
    consulta = "SELECT COUNT(*) AS n FROM Topicos_Algebra LIMIT 1"
    antes = db.execute_readonly(consulta)
    monkeypatch.setattr(database, "validate_select", lambda sql, *a, **k: sql)
    with pytest.raises(SQLExecucaoError):
        db.execute_readonly(
            "INSERT INTO Topicos_Algebra (nome, descricao, resumo_teorico) "
            "VALUES ('x', 'y', 'z')"
        )
    monkeypatch.undo()
    assert db.execute_readonly(consulta) == antes


def test_ensure_ready_usa_transacao_imediata(tmp_path, monkeypatch):
    # BEGIN IMMEDIATE faz uma 1ª execução concorrente esperar, em vez de falhar
    # ao promover um BEGIN adiado a escrita.
    executados: list[str] = []
    conectar = sqlite3.connect

    class _Espiao:
        def __init__(self, conn):
            self._conn = conn

        def execute(self, sql, *args):
            executados.append(sql)
            return self._conn.execute(sql, *args)

        def close(self):
            self._conn.close()

    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: _Espiao(conectar(*a, **k)))
    Database(tmp_path / "edu.db").ensure_ready()
    assert "BEGIN IMMEDIATE" in executados
    assert "BEGIN" not in executados
