"""Acesso ao banco SQLite local.

Esta parte contém o validador de SQL gerado pelo LLM. Ele é uma checagem
razoável para a PoC, não um parser SQL completo: a conexão somente leitura é a
segunda barreira, independente dele.
"""
from exceptions import SQLRejeitadoError

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
    if not valor.isdigit():
        raise _reject("LIMIT deve ser um inteiro")
    if int(valor) > max_limit:
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
