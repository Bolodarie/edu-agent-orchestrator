"""Validador de LaTeX: embrulha em bloco de código parágrafos com LaTeX quebrado."""
import re

_FENCE = re.compile(r"^\s*```")
_PARAGRAPH_SPLIT = re.compile(r"(\n\s*\n)")
_ESCAPED = re.compile(r"\\[\\${}]")
_DOLLARS = re.compile(r"\$\$|\$")
_LEFT = re.compile(r"\\left(?![A-Za-z])")
_RIGHT = re.compile(r"\\right(?![A-Za-z])")
_ENV = re.compile(r"\\(begin|end)\{([^{}]*)\}")


def _dollars_balanced(text: str) -> bool:
    state = None  # None, "$" (inline) ou "$$" (bloco)
    for token in _DOLLARS.findall(text):
        if state is None:
            state = token
        elif state == token:
            state = None
        else:
            return False
    return state is None


def _braces_balanced(text: str) -> bool:
    depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _environments_balanced(text: str) -> bool:
    stack = []
    for kind, name in _ENV.findall(text):
        if kind == "begin":
            stack.append(name)
        elif not stack or stack.pop() != name:
            return False
    return not stack


def _paragraph_is_valid(paragraph: str) -> bool:
    cleaned = _ESCAPED.sub("", paragraph)
    return (
        _dollars_balanced(cleaned)
        and _braces_balanced(cleaned)
        and len(_LEFT.findall(paragraph)) == len(_RIGHT.findall(paragraph))
        and _environments_balanced(paragraph)
    )


def _split_fenced(text: str):
    """Divide o texto em (is_code, trecho), preservando todos os caracteres."""
    segments = []
    current: list = []
    in_code = False
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            if not in_code:
                if current:
                    segments.append((False, "".join(current)))
                current = [line]
                in_code = True
            else:
                current.append(line)
                segments.append((True, "".join(current)))
                current = []
                in_code = False
        else:
            current.append(line)
    if current:
        segments.append((in_code, "".join(current)))
    return segments


def validate_latex(text: str) -> "tuple[str, list[str]]":
    """Devolve (texto saneado, avisos); embrulha parágrafos com LaTeX inválido."""
    warnings: list = []
    output: list = []
    for is_code, segment in _split_fenced(text):
        if is_code:
            output.append(segment)
            continue
        for part in _PARAGRAPH_SPLIT.split(segment):
            if not part.strip() or _PARAGRAPH_SPLIT.fullmatch(part):
                output.append(part)
            elif _paragraph_is_valid(part):
                output.append(part)
            else:
                excerpt = " ".join(part.split())[:40]
                warnings.append(
                    f"Fórmula LaTeX malformada (cifrão, chave ou ambiente sem par) "
                    f"no parágrafo \"{excerpt}\"; exibido como código."
                )
                body = part.strip()
                lead = part[: len(part) - len(part.lstrip())]
                trail = part[len(part.rstrip()):]
                output.append(f"{lead}```\n{body}\n```{trail}")
    return "".join(output), warnings
