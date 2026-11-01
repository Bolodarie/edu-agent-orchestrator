"""Fronteiras entre camadas (spec 4.1), verificadas lendo os imports via ``ast``."""

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
STDLIB = set(sys.stdlib_module_names)
# Módulos do próprio projeto: arquivos .py e pacotes na raiz.
INTERNOS = {p.stem for p in RAIZ.glob("*.py")} | {
    p.name for p in RAIZ.iterdir() if (p / "__init__.py").exists()
}


def imports_of(source: str) -> set[str]:
    """Nomes de módulo de topo importados por ``source`` (``import x.y`` -> ``x``)."""
    modulos: set[str] = set()
    for no in ast.walk(ast.parse(source)):
        if isinstance(no, ast.Import):
            modulos.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            modulos.add(no.module.split(".")[0])
    return modulos


def _imports_do_arquivo(caminho: Path) -> set[str]:
    return imports_of(caminho.read_text(encoding="utf-8"))


def _arquivos_dos_agentes() -> list[Path]:
    arquivos = sorted((RAIZ / "agents").glob("*.py"))
    assert arquivos, "nenhum arquivo encontrado em agents/"
    return arquivos


def test_imports_of_detecta_violacao():
    assert imports_of("import database") == {"database"}
    assert imports_of("from database import Database") == {"database"}
    assert imports_of("import os.path\nfrom agents.query import QueryAgent") == {
        "os",
        "agents",
    }
    assert imports_of("def f():\n    import llm\n") == {"llm"}
    assert imports_of("x = 1") == set()


def test_app_importa_so_orchestrator_e_models():
    permitidos = {"streamlit", "orchestrator", "models"} | (STDLIB - {"importlib"})
    extras = _imports_do_arquivo(RAIZ / "app.py") - permitidos
    assert not extras, f"app.py importa módulos proibidos: {sorted(extras)}"


def test_agents_nao_importam_database():
    proibidos = {"database", "orchestrator", "app", "importlib"}
    for arquivo in _arquivos_dos_agentes():
        violacoes = _imports_do_arquivo(arquivo) & proibidos
        assert not violacoes, f"{arquivo.name} importa {sorted(violacoes)}"


def test_database_nao_importa_agentes_nem_llm():
    proibidos = {"agents", "llm", "orchestrator", "app", "importlib"}
    violacoes = _imports_do_arquivo(RAIZ / "database.py") & proibidos
    assert not violacoes, f"database.py importa {sorted(violacoes)}"


def test_agents_so_dependem_do_permitido():
    permitidos = {"llm", "models", "exceptions"}
    for arquivo in _arquivos_dos_agentes():
        internos = (_imports_do_arquivo(arquivo) & INTERNOS) - {"agents"}
        extras = internos - permitidos
        assert not extras, f"{arquivo.name} depende de {sorted(extras)}"


def uses_dynamic_import(source: str) -> bool:
    """Detecta ``__import__``, ``import importlib`` e ``importlib.import_module``,
    que contornariam a checagem estática de imports."""
    for no in ast.walk(ast.parse(source)):
        if isinstance(no, ast.Name) and no.id == "__import__":
            return True
        if isinstance(no, ast.Attribute) and no.attr in {"import_module", "__import__"}:
            return True
        if isinstance(no, ast.Name) and no.id == "import_module":
            return True
    return "importlib" in imports_of(source)


def test_uses_dynamic_import_detecta_violacao():
    assert uses_dynamic_import("m = __import__('database')")
    assert uses_dynamic_import("import importlib\nimportlib.import_module('database')")
    assert uses_dynamic_import("from importlib import import_module\nimport_module('x')")
    assert uses_dynamic_import("import importlib as il\nil.import_module('x')")
    assert uses_dynamic_import("import importlib")
    assert not uses_dynamic_import("import os\nx = os.path.join('a', 'b')")


def test_sem_import_dinamico_nas_camadas_restritas():
    arquivos = [RAIZ / "app.py", RAIZ / "database.py", *_arquivos_dos_agentes()]
    for arquivo in arquivos:
        fonte = arquivo.read_text(encoding="utf-8")
        assert not uses_dynamic_import(fonte), f"{arquivo.name} usa import dinâmico"
