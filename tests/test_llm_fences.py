from llm import strip_code_fences


def test_cerca_sem_linguagem():
    assert strip_code_fences("```\nSELECT 1\n```") == "SELECT 1"


def test_cerca_com_tag_de_linguagem():
    assert strip_code_fences('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_cerca_sem_quebra_antes_do_fechamento():
    assert strip_code_fences("```sql\nSELECT 1```") == "SELECT 1"


def test_texto_sem_cerca_volta_aparado():
    assert strip_code_fences("  SELECT 1 LIMIT 1\n") == "SELECT 1 LIMIT 1"


def test_texto_sem_cerca_inalterado():
    assert strip_code_fences("SELECT 1") == "SELECT 1"


def test_string_vazia():
    assert strip_code_fences("") == ""


def test_cerca_vazia():
    assert strip_code_fences("```\n```") == ""
