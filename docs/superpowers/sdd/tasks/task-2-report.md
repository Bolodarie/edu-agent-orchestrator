# Task 2 report: latex_validator.py

Status: DONE
Commit: d3391b6 feat: add LaTeX validator (worktree edu-agent-orchestrator-wt/t2, branch task/t2-latex)

## Implementation
`latex_validator.py` (stdlib only, Python 3.10): `validate_latex(text) -> tuple[str, list[str]]`.
- Splits text line by line into fenced (```) and unfenced segments; fenced segments are copied untouched.
- Unfenced segments are split on `\n\s*\n` (separators preserved, so valid text round-trips byte-identical).
- Paragraph validity: strip `\\`, `\$`, `\{`, `\}` escapes, then check (a) `$`/`$$` pairing via a state scan (inline and display cannot interleave), (b) brace depth never negative and ends at 0, (c) count of `\left` == `\right` (regex excludes `\leftarrow`/`\rightarrow`), (d) `\begin{x}`/`\end{x}` matched as a stack with equal names.
- Invalid paragraph becomes "```\n<paragraph>\n```" with one pt-BR warning including a 40-char excerpt.

## Tests
`tests/test_latex_validator.py`: the 9 tests from the brief. Result: 9 passed; full suite in worktree 13 passed.

## TDD evidence
RED: `.venv/bin/python -m pytest tests/test_latex_validator.py -v` -> `ModuleNotFoundError: No module named 'latex_validator'` (collection error, 1 error).
GREEN: same command -> `9 passed in 0.01s`.

## Files changed
- latex_validator.py (new)
- tests/test_latex_validator.py (new)

## Self-review / concerns
- Brace balance is checked on the whole paragraph, not only inside math, so plain prose with a lone `{` gets wrapped (matches spec wording).
- An unclosed fence at end of text is treated as code to the end.
- `$a $$ b` (inline/display interleaved) is considered invalid.
- No concerns blocking.

## Fix round 1 (review finding: whitespace dropped when wrapping)
Problem: wrapper used `part.strip()`, dropping the trailing newline, so an invalid paragraph directly before a fence produced a six-backtick line, and trailing `\n` was lost.
Change (latex_validator.py): wrapper now preserves the paragraph's original leading/trailing whitespace: `f"{lead}```\n{body}\n```{trail}"`.
Tests added: `test_paragrafo_ruim_colado_numa_cerca` (input `"Valor $x+1\n```\ncode\n```\n"` -> `"```\nValor $x+1\n```\n```\ncode\n```\n"`, no "``````"), `test_newline_final_preservado` (`"Texto $x+1\n"` -> `"```\nTexto $x+1\n```\n"`).
RED: `.venv/bin/python -m pytest tests/test_latex_validator.py -q` -> `2 failed, 9 passed`.
GREEN: same command (-v) -> `11 passed in 0.01s`.
Commit: fix: preserve surrounding whitespace when wrapping invalid LaTeX paragraph

## Fix round 2 (regression: indented paragraph produced indented opening fence)
Change (latex_validator.py): `lead`/`trail` now keep only the newline characters of the surrounding whitespace (horizontal indentation dropped), so the opening fence always starts at column 0; round-1 behaviors (adjacent fence, trailing newline) preserved.
Test added: `test_paragrafo_ruim_indentado_abre_cerca_na_coluna_zero` (`"Texto\n\n    Valor $x+1\n\nFim"` -> `"Texto\n\n```\nValor $x+1\n```\n\nFim"`).
RED: `.venv/bin/python -m pytest tests/test_latex_validator.py -q` -> `1 failed, 11 passed`.
GREEN: same command -> `12 passed`.
Commit: fix: keep wrapper fence at column 0 for indented invalid paragraphs
