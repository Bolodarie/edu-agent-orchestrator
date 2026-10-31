"""Acesso ao banco SQLite local.

Contém o validador de SQL gerado pelo LLM, o schema com seed e a classe
`Database`. O validador é uma checagem razoável para a PoC, não um parser SQL
completo: a conexão somente leitura é a segunda barreira, independente dele.
Por isso a conexão de leitura nunca habilita o carregamento de extensões
(`enable_load_extension`), já que o validador não bloqueia `load_extension(...)`.
"""
import sqlite3
from pathlib import Path
from typing import Any, Union

from exceptions import SQLExecucaoError, SQLRejeitadoError

# --- Validador de SQL --------------------------------------------------------

ALLOWED_TABLES: frozenset[str] = frozenset({"Topicos_Algebra", "Exercicios", "Resolucoes"})
MAX_LIMIT = 50

_FORBIDDEN_WORDS = frozenset(
    {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "ATTACH", "DETACH", "PRAGMA", "REPLACE", "VACUUM",
        # CTEs são rejeitadas em qualquer posição, não só como primeira palavra.
        "WITH",
    }
)
# Palavras que encerram a lista de tabelas de uma cláusula FROM.
_END_OF_FROM = frozenset(
    {"WHERE", "GROUP", "ORDER", "HAVING", "LIMIT", "UNION", "INTERSECT",
     "EXCEPT", "WINDOW"}
)
# Caracteres que abrem identificadores entre aspas; não são suportados.
_QUOTED_IDENT_CHARS = frozenset('"`[]')

# Um token é (tipo, valor, posição inicial); tipo: word | number | string | punct.
_Token = tuple


def _reject(motivo: str) -> SQLRejeitadoError:
    return SQLRejeitadoError(f"SQL rejeitado: {motivo}")


def _tokenize(sql: str) -> list:
    """Quebra o SQL em tokens, respeitando literais '...' (com '' escapado).

    Rejeita comentários e identificadores entre aspas fora de literais, e
    literais não terminados.
    """
    tokens: list = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch.isspace():
            i += 1
        elif ch == "'":
            start = i
            i += 1
            while True:
                if i >= n:
                    raise _reject("literal de texto não terminado")
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            tokens.append(("string", sql[start:i], start))
        elif sql.startswith("--", i) or sql.startswith("/*", i):
            raise _reject("comentários não são permitidos")
        elif ch in _QUOTED_IDENT_CHARS:
            raise _reject("identificadores entre aspas não são permitidos")
        elif ch.isalpha() or ch == "_":
            start = i
            while i < n and (sql[i].isalnum() or sql[i] == "_"):
                i += 1
            tokens.append(("word", sql[start:i], start))
        elif ch.isascii() and ch.isdigit():
            start = i
            while i < n and (sql[i].isalnum() or sql[i] in "._"):
                i += 1
            tokens.append(("number", sql[start:i], start))
        else:
            tokens.append(("punct", ch, i))
            i += 1
    return tokens


def _strip_trailing_semicolon(sql: str, tokens: list) -> list:
    """Tolera um único ';' final; qualquer outro ';' significa várias instruções."""
    if tokens and tokens[-1][:2] == ("punct", ";"):
        tokens = tokens[:-1]
    if any(t[:2] == ("punct", ";") for t in tokens):
        raise _reject("apenas uma instrução é permitida")
    return tokens


def _is_word(token: _Token, word: str) -> bool:
    return token[0] == "word" and token[1].upper() == word


def _check_statement_start(tokens: list) -> None:
    if not tokens:
        raise _reject("consulta vazia")
    if not _is_word(tokens[0], "SELECT"):
        raise _reject("a consulta deve começar com SELECT")


def _check_forbidden_words(tokens: list) -> None:
    for kind, value, _ in tokens:
        if kind == "word" and value.upper() in _FORBIDDEN_WORDS:
            raise _reject(f"palavra proibida: {value.upper()}")


def _check_tables(tokens: list, allowed: frozenset) -> None:
    """Todo identificador após FROM/JOIN (e após vírgula numa lista de FROM)
    deve estar em `allowed`. Aliases não são verificados. Também confere o
    balanceamento de parênteses."""
    allowed_lower = {name.lower() for name in allowed}
    in_from = [False]  # uma entrada por nível de parênteses
    expect_table = False
    for idx, token in enumerate(tokens):
        kind, value, _ = token
        if expect_table:
            expect_table = False
            if kind == "word":
                if value.lower() not in allowed_lower:
                    raise _reject(f"tabela não permitida: {value}")
                nxt = tokens[idx + 1] if idx + 1 < len(tokens) else None
                if nxt is not None and nxt[:2] in (("punct", "."), ("punct", "(")):
                    raise _reject("referência de tabela não suportada")
                continue
            if token[:2] == ("punct", "("):
                nxt = tokens[idx + 1] if idx + 1 < len(tokens) else None
                if nxt is None or not _is_word(nxt, "SELECT"):
                    raise _reject("apenas subconsultas SELECT são permitidas em FROM")
                in_from.append(False)
                continue
            raise _reject("tabela esperada após FROM/JOIN")

        if kind == "punct":
            if value == "(":
                in_from.append(False)
            elif value == ")":
                if len(in_from) == 1:
                    raise _reject("parênteses desbalanceados")
                in_from.pop()
            elif value == "," and in_from[-1]:
                expect_table = True
        elif kind == "word":
            upper = value.upper()
            if upper == "FROM":
                # "IS [NOT] DISTINCT FROM" não introduz uma tabela.
                if idx > 0 and _is_word(tokens[idx - 1], "DISTINCT"):
                    continue
                in_from[-1] = True
                expect_table = True
            elif upper == "JOIN":
                expect_table = True
            elif upper in _END_OF_FROM:
                in_from[-1] = False
    if expect_table:
        raise _reject("tabela esperada após FROM/JOIN")
    if len(in_from) != 1:
        raise _reject("parênteses desbalanceados")


def _check_final_limit(tokens: list, max_limit: int) -> None:
    """Exige `LIMIT <inteiro>` como os dois últimos tokens (nível superior, já
    que os parênteses estão balanceados) e valor <= max_limit."""
    if len(tokens) < 3 or not _is_word(tokens[-2], "LIMIT") or tokens[-1][0] != "number":
        raise _reject("a consulta deve terminar com LIMIT <inteiro>")
    valor = tokens[-1][1]
    if not (valor.isascii() and valor.isdigit()):
        raise _reject("LIMIT deve ser um inteiro")
    # Limita o tamanho antes de int(): evita ValueError em literais gigantes.
    if len(valor) > 18 or int(valor) > max_limit:
        raise _reject(f"LIMIT máximo é {max_limit}")


def validate_select(
    sql: str,
    allowed_tables: frozenset[str] = ALLOWED_TABLES,
    max_limit: int = MAX_LIMIT,
) -> str:
    """Valida um SELECT somente leitura. Devolve o SQL sem o ';' final ou
    levanta SQLRejeitadoError."""
    if not isinstance(sql, str):
        raise _reject("o SQL deve ser texto")
    tokens = _strip_trailing_semicolon(sql, _tokenize(sql))
    _check_statement_start(tokens)
    _check_forbidden_words(tokens)
    _check_tables(tokens, allowed_tables)
    _check_final_limit(tokens, max_limit)
    # O ';' final (se houver) começa depois do último token restante.
    _, last_value, last_start = tokens[-1]
    return sql[: last_start + len(last_value)].strip()


# --- Schema e seed -----------------------------------------------------------

SCHEMA_DESCRIPTION = """\
Tabelas do banco SQLite (somente leitura):

Topicos_Algebra(id, nome, descricao, resumo_teorico)
  - nome: nome do tópico (ex.: 'Equação do 2º Grau')
  - resumo_teorico: resumo da teoria em Markdown com LaTeX

Exercicios(id, topico_id, enunciado_latex, dificuldade)
  - topico_id referencia Topicos_Algebra.id
  - dificuldade: 'fácil', 'média' ou 'difícil'
  - enunciado_latex: enunciado em LaTeX puro, sem delimitadores $

Resolucoes(id, exercicio_id, passo_a_passo_latex)
  - exercicio_id referencia Exercicios.id
  - passo_a_passo_latex: resolução passo a passo em LaTeX puro, sem delimitadores $
"""

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS Topicos_Algebra (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT NOT NULL,
    resumo_teorico TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Exercicios (
    id INTEGER PRIMARY KEY,
    topico_id INTEGER NOT NULL REFERENCES Topicos_Algebra(id),
    enunciado_latex TEXT NOT NULL,
    dificuldade TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Resolucoes (
    id INTEGER PRIMARY KEY,
    exercicio_id INTEGER NOT NULL REFERENCES Exercicios(id),
    passo_a_passo_latex TEXT NOT NULL
);
"""


def _aligned(*linhas: str) -> str:
    """Monta um bloco `aligned` (LaTeX puro, sem linhas em branco)."""
    corpo = " \\\\\n".join(linhas)
    return "\\begin{aligned}\n" + corpo + "\n\\end{aligned}"


# Cada tópico: (nome, descricao, resumo_teorico, [(enunciado, dificuldade, resolucao)]).
# enunciado e resolucao são LaTeX puro, sem `$`; o formatador os embrulha em $$...$$.
_SEED: list = [
    (
        "Equação do 1º Grau",
        "Equações da forma ax + b = 0, com a diferente de zero.",
        "Uma **equação do 1º grau** tem a forma $ax + b = 0$, com $a \\neq 0$.\n\n"
        "Para resolver, isole a incógnita usando operações inversas dos dois lados:\n\n"
        "- some ou subtraia o mesmo valor dos dois lados;\n"
        "- multiplique ou divida os dois lados pelo mesmo número não nulo.\n\n"
        "A solução é $x = -\\frac{b}{a}$.",
        [
            (
                "2x + 6 = 14",
                "fácil",
                _aligned("2x + 6 &= 14", "2x &= 14 - 6", "2x &= 8", "x &= 4"),
            ),
            (
                "5(x - 2) = 3x + 4",
                "média",
                _aligned(
                    "5x - 10 &= 3x + 4",
                    "5x - 3x &= 4 + 10",
                    "2x &= 14",
                    "x &= 7",
                ),
            ),
            (
                "\\frac{x}{3} + \\frac{x}{4} = 7",
                "difícil",
                _aligned(
                    "\\frac{4x}{12} + \\frac{3x}{12} &= 7",
                    "\\frac{7x}{12} &= 7",
                    "7x &= 84",
                    "x &= 12",
                ),
            ),
        ],
    ),
    (
        "Equação do 2º Grau",
        "Equações da forma ax² + bx + c = 0, resolvidas com a fórmula de Bhaskara.",
        "Uma **equação do 2º grau** tem a forma $ax^2 + bx + c = 0$, com $a \\neq 0$.\n\n"
        "Calcule o discriminante $\\Delta = b^2 - 4ac$ e use a fórmula de Bhaskara: "
        "$x = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}$.\n\n"
        "- Se $\\Delta > 0$, há duas raízes reais distintas.\n"
        "- Se $\\Delta = 0$, há uma raiz real dupla.\n"
        "- Se $\\Delta < 0$, não há raízes reais.",
        [
            (
                "x^2 - 5x + 6 = 0",
                "fácil",
                _aligned(
                    "\\Delta &= (-5)^2 - 4 \\cdot 1 \\cdot 6 = 25 - 24 = 1",
                    "x &= \\frac{5 \\pm 1}{2}",
                    "x_1 &= 3 \\quad \\text{e} \\quad x_2 = 2",
                ),
            ),
            (
                "x^2 - 6x + 9 = 0",
                "média",
                _aligned(
                    "\\Delta &= (-6)^2 - 4 \\cdot 1 \\cdot 9 = 36 - 36 = 0",
                    "x &= \\frac{6 \\pm 0}{2}",
                    "x &= 3 \\quad \\text{(raiz dupla)}",
                ),
            ),
            (
                "2x^2 + 3x - 2 = 0",
                "difícil",
                _aligned(
                    "\\Delta &= 3^2 - 4 \\cdot 2 \\cdot (-2) = 9 + 16 = 25",
                    "x &= \\frac{-3 \\pm 5}{4}",
                    "x_1 &= \\frac{1}{2} \\quad \\text{e} \\quad x_2 = -2",
                ),
            ),
        ],
    ),
    (
        "Sistemas Lineares",
        "Sistemas de duas equações do 1º grau com duas incógnitas.",
        "Um **sistema linear** 2x2 reúne duas equações do 1º grau com as mesmas "
        "incógnitas $x$ e $y$.\n\n"
        "Dois métodos clássicos:\n\n"
        "- **Substituição:** isole uma incógnita em uma equação e substitua na outra.\n"
        "- **Adição:** some as equações (multiplicando-as, se preciso) para eliminar "
        "uma incógnita.\n\n"
        "A solução é o par $(x, y)$ que satisfaz as duas equações ao mesmo tempo.",
        [
            (
                "\\begin{cases} x + y = 10 \\\\ x - y = 2 \\end{cases}",
                "fácil",
                _aligned(
                    "(x + y) + (x - y) &= 10 + 2",
                    "2x &= 12",
                    "x &= 6",
                    "y &= 10 - 6 = 4",
                ),
            ),
            (
                "\\begin{cases} 2x + 3y = 12 \\\\ x - y = 1 \\end{cases}",
                "média",
                _aligned(
                    "x &= y + 1",
                    "2(y + 1) + 3y &= 12",
                    "5y &= 10",
                    "y &= 2",
                    "x &= 3",
                ),
            ),
            (
                "\\begin{cases} 2x + y = 7 \\\\ 3x - 2y = 7 \\end{cases}",
                "difícil",
                _aligned(
                    "4x + 2y &= 14 \\quad \\text{(primeira equação vezes 2)}",
                    "(4x + 2y) + (3x - 2y) &= 14 + 7",
                    "7x &= 21",
                    "x &= 3",
                    "y &= 7 - 2 \\cdot 3 = 1",
                ),
            ),
        ],
    ),
    (
        "Fatoração",
        "Escrever expressões algébricas como produto de fatores.",
        "**Fatorar** é escrever uma expressão como um produto de fatores.\n\n"
        "Casos mais comuns:\n\n"
        "- **Fator comum:** $ax + ay = a(x + y)$.\n"
        "- **Diferença de quadrados:** $a^2 - b^2 = (a - b)(a + b)$.\n"
        "- **Trinômio quadrado perfeito:** $a^2 + 2ab + b^2 = (a + b)^2$.",
        [
            (
                "x^2 - 9",
                "fácil",
                _aligned("x^2 - 9 &= x^2 - 3^2", "&= (x - 3)(x + 3)"),
            ),
            (
                "x^2 + 6x + 9",
                "média",
                _aligned(
                    "x^2 + 6x + 9 &= x^2 + 2 \\cdot x \\cdot 3 + 3^2",
                    "&= (x + 3)^2",
                ),
            ),
            (
                "2x^2 - 8",
                "difícil",
                _aligned(
                    "2x^2 - 8 &= 2(x^2 - 4)",
                    "&= 2(x^2 - 2^2)",
                    "&= 2(x - 2)(x + 2)",
                ),
            ),
        ],
    ),
]


def _seed(conn: sqlite3.Connection) -> None:
    for nome, descricao, resumo, exercicios in _SEED:
        cur = conn.execute(
            "INSERT INTO Topicos_Algebra (nome, descricao, resumo_teorico) VALUES (?, ?, ?)",
            (nome, descricao, resumo),
        )
        topico_id = cur.lastrowid
        for enunciado, dificuldade, resolucao in exercicios:
            cur = conn.execute(
                "INSERT INTO Exercicios (topico_id, enunciado_latex, dificuldade) "
                "VALUES (?, ?, ?)",
                (topico_id, enunciado, dificuldade),
            )
            conn.execute(
                "INSERT INTO Resolucoes (exercicio_id, passo_a_passo_latex) VALUES (?, ?)",
                (cur.lastrowid, resolucao),
            )


def _dict_row(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: valor for col, valor in zip(cursor.description, row)}


# --- Banco -------------------------------------------------------------------


class Database:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self.schema_description: str = SCHEMA_DESCRIPTION

    def ensure_ready(self) -> None:
        """Cria diretório, arquivo, schema e seed. Idempotente.

        É o único lugar com conexão de escrita; schema e seed entram na mesma
        transação, então uma falha não deixa o banco pela metade.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("BEGIN")
            try:
                for instrucao in _SCHEMA_SQL.split(";"):
                    if instrucao.strip():
                        conn.execute(instrucao)
                if conn.execute("SELECT COUNT(*) FROM Topicos_Algebra").fetchone()[0] == 0:
                    _seed(conn)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

    def execute_readonly(self, sql: str) -> list:
        """Valida e executa um SELECT numa conexão somente leitura.

        SQLRejeitadoError (do validador) propaga sem alteração; só erros do
        SQLite viram SQLExecucaoError. Não chama `enable_load_extension`.
        """
        sql_validado = validate_select(sql)
        uri = f"{self.path.resolve().as_uri()}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True)
            try:
                conn.row_factory = _dict_row
                return conn.execute(sql_validado).fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise SQLExecucaoError(f"Erro ao executar o SQL: {exc}") from exc
