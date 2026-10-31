from latex_validator import validate_latex


def test_valido_passa_intacto():
    texto = "Resolva $x^2=4$.\n\n$$\\frac{a}{b}$$"
    saida, avisos = validate_latex(texto)
    assert saida == texto
    assert avisos == []


def test_dolar_sem_par():
    saida, avisos = validate_latex("Valor $x+1")
    assert "```" in saida
    assert "Valor $x+1" in saida
    assert len(avisos) == 1


def test_chaves_desbalanceadas():
    saida, avisos = validate_latex("$\\frac{a}{b$")
    assert "```" in saida
    assert len(avisos) == 1


def test_begin_end_sem_par():
    saida, avisos = validate_latex("$$\\begin{aligned} x=1 $$")
    assert "```" in saida
    assert len(avisos) == 1


def test_left_right_sem_par():
    saida, avisos = validate_latex("$\\left( x $")
    assert "```" in saida
    assert len(avisos) == 1


def test_cifrao_escapado_nao_conta():
    texto = "Custa \\$5 hoje"
    saida, avisos = validate_latex(texto)
    assert saida == texto
    assert avisos == []


def test_bloco_duplo_multilinha_no_mesmo_paragrafo():
    texto = "$$\n\\begin{aligned}\nx&=1\\\\\ny&=2\n\\end{aligned}\n$$"
    saida, avisos = validate_latex(texto)
    assert saida == texto
    assert avisos == []


def test_bloco_de_codigo_e_ignorado():
    texto = "Exemplo:\n\n```\npreco = $ 5 e $x\n```\n\nFim."
    saida, avisos = validate_latex(texto)
    assert saida == texto
    assert avisos == []


def test_so_o_paragrafo_ruim_e_embrulhado():
    bom = "Resolva $x^2=4$."
    ruim = "Valor $x+1"
    saida, avisos = validate_latex(f"{bom}\n\n{ruim}")
    assert len(avisos) == 1
    primeira, _, resto = saida.partition("\n\n")
    assert primeira == bom
    assert "```" not in primeira
    assert resto == f"```\n{ruim}\n```"
