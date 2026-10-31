import pytest

from database import ALLOWED_TABLES, MAX_LIMIT, validate_select
from exceptions import SQLRejeitadoError


def test_constantes_publicas():
    assert ALLOWED_TABLES == frozenset({"Topicos_Algebra", "Exercicios", "Resolucoes"})
    assert MAX_LIMIT == 50


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT t.nome FROM Topicos_Algebra t LIMIT 3",
        "SELECT t.nome FROM Topicos_Algebra t LIMIT 3;",
        "SELECT e.enunciado FROM Exercicios e JOIN Topicos_Algebra t "
        "ON e.topico_id = t.id LIMIT 5",
        "SELECT t.nome FROM Topicos_Algebra t WHERE t.nome LIKE '%2º Grau%' LIMIT 5",
        "SELECT t.nome FROM Topicos_Algebra t WHERE t.nome LIKE '%drop; x%' LIMIT 5",
        "SELECT * FROM Exercicios LIMIT 50",
        "select * from exercicios limit 5",
        "SELECT * FROM Exercicios WHERE id IN (SELECT exercicio_id FROM Resolucoes) LIMIT 5",
        "SELECT * FROM (SELECT * FROM Exercicios) x LIMIT 5",
        "SELECT * FROM Exercicios WHERE enunciado LIKE 'it''s; -- /* ok' LIMIT 5",
    ],
)
def test_sql_aceito_devolve_string(sql):
    resultado = validate_select(sql)
    assert isinstance(resultado, str)
    assert not resultado.rstrip().endswith(";")


def test_remove_ponto_e_virgula_final():
    assert (
        validate_select("SELECT t.nome FROM Topicos_Algebra t LIMIT 3;  ")
        == "SELECT t.nome FROM Topicos_Algebra t LIMIT 3"
    )


def test_respeita_parametros_customizados():
    assert validate_select("SELECT * FROM Outra LIMIT 5", frozenset({"Outra"}))
    with pytest.raises(SQLRejeitadoError):
        validate_select("SELECT * FROM Exercicios LIMIT 11", max_limit=10)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE Exercicios",
        "SELECT 1; DROP TABLE Exercicios LIMIT 1",
        "SELECT * FROM Usuarios LIMIT 1",
        "SELECT * FROM Exercicios",
        "SELECT * FROM Exercicios LIMIT 51",
        "SELECT * FROM Exercicios LIMIT 5 -- x",
        "SELECT * FROM Exercicios /* x */ LIMIT 5",
        "WITH x AS (SELECT 1) SELECT * FROM x LIMIT 1",
        "SELECT * FROM Exercicios WHERE id IN (SELECT id FROM Usuarios) LIMIT 5",
        "SELECT * FROM Exercicios LIMIT 5; DELETE FROM Exercicios",
        "",
        "   ",
        # Casos extras de robustez.
        "SELECT * FROM Exercicios, Usuarios LIMIT 5",
        "SELECT * FROM Exercicios e JOIN Usuarios u ON e.id = u.id LIMIT 5",
        'SELECT * FROM "Usuarios" LIMIT 5',
        "SELECT * FROM main.Exercicios LIMIT 5",
        "SELECT * FROM Exercicios LIMIT 5 OFFSET 2",
        "SELECT * FROM Exercicios LIMIT 5, 10",
        "SELECT * FROM Exercicios LIMIT -1",
        "SELECT * FROM Exercicios LIMIT 5.5",
        "SELECT * FROM Exercicios LIMIT x",
        "SELECT * FROM Exercicios WHERE id IN (SELECT id FROM Exercicios LIMIT 5",
        "SELECT * FROM (SELECT * FROM Exercicios LIMIT 5)",
        "SELECT * FROM Exercicios WHERE enunciado = 'abc LIMIT 5",
        "SELECT * FROM Exercicios;; LIMIT 5",
        "SELECT * FROM Exercicios LIMIT 5;;",
        "SELECT * FROM Exercicios WHERE x = 1 UPDATE y LIMIT 5",
        "SELECT * FROM (WITH x AS (SELECT 1) SELECT * FROM x) LIMIT 5",
        "SELECT * FROM (Exercicios) LIMIT 5",
        "EXPLAIN SELECT * FROM Exercicios LIMIT 5",
        "PRAGMA table_info(Exercicios)",
    ],
)
def test_sql_rejeitado(sql):
    with pytest.raises(SQLRejeitadoError):
        validate_select(sql)


def test_nao_string_e_rejeitado():
    with pytest.raises(SQLRejeitadoError):
        validate_select(None)  # type: ignore[arg-type]
