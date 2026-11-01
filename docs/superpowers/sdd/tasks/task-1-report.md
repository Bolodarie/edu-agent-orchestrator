# Task 1 report: Scaffold, contratos e exceções

Status: DONE_WITH_CONCERNS (minor, env only)
Commit: 9219287 feat: scaffold, contracts and exceptions

## Implemented
requirements.txt, requirements-dev.txt, pytest.ini, agents/__init__.py, tests/__init__.py,
tests/test_models.py, models.py (Intent, RouterResult, QueryAttempt, Trace, Status,
OrchestratorResponse; Pydantic v2, default_factory for list/dict), exceptions.py
(AgentPipelineError + 4 children, recuperavel as class attr). Python 3.10 compatible (`X | None` is OK in pydantic on 3.10).

## TDD evidence
RED: `.venv/bin/python -m pytest tests/test_models.py -v` ->
`ModuleNotFoundError: No module named 'exceptions'` (collection error, 1 error).
GREEN: same command -> 4 passed in 0.05s (all four tests PASSED).

## Environment note / concern
`python3 -m venv` failed (python3.10-venv/ensurepip missing; no sudo). Used
`uv venv --system-site-packages --python 3.10 .venv` instead; pytest 9.1.1, pydantic 2.12.3 and
streamlit resolve from system site. `pip install -r requirements-dev.txt` was NOT run
(nothing installed globally; deps already present). .venv is gitignored.

## Self-review
Tests match the brief; the Trace test uses QueryAttempt for attempts and also checks avisos and tempos_ms isolation. No attribution in commit. Only brief files committed.
