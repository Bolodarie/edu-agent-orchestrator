# edu-agent-orchestrator

PoC de portfólio: assistente educacional de álgebra (cursinho popular) com arquitetura multi-agente, Python + Streamlit + SQLite. O objetivo é **demonstrar desenho de arquitetura e separação de camadas**, não evoluir um produto.

Design completo e aprovado: `docs/superpowers/specs/2026-10-31-edu-agent-orchestrator-design.md`. Em caso de dúvida, ele manda; se for preciso divergir, atualize o documento junto.

## Comandos

```bash
pip install -r requirements-dev.txt # runtime (streamlit, pydantic) + pytest; rodar só o app exige apenas requirements.txt
streamlit run app.py                # demo
pytest                              # suíte de testes
```

## Regra de dependência (inegociável)

```
app.py  ──►  orchestrator.py  ──►  agents/*  ──►  llm.py
                    └──────────►  database.py
```

- `app.py` importa **só** `orchestrator` e `models`. Nunca `database`, `agents`, `llm`.
- `agents/` importa `llm`, `models`, `exceptions`. **Nunca** `database`.
- `database.py` não conhece agentes nem LLM.
- Só o orquestrador enxerga agentes e banco juntos.
- `tests/` tem um teste (via `ast`) que falha se qualquer uma dessas fronteiras for violada. Não enfraqueça esse teste para fazer código passar; corrija o import.

## Decisões de design que não se mudam sem conversar

- **LLM injetado:** agentes recebem um `LLMClient` (`Protocol`) no construtor. Hoje só existe `MockLLMClient`; nenhum SDK de LLM entra nas dependências. Trocar por LLM real = nova classe + uma linha em `build_orchestrator()`.
- **SQL da LLM é não confiável:** o validador e a conexão somente leitura ficam em `database.py`, independentes do agente. Nunca execute SQL de agente sem passar por `execute_readonly`.
- **Orquestrador stateless:** `handle(texto) -> OrchestratorResponse`. Histórico do chat vive só em `st.session_state` para renderização.
- **Erros:** camadas inferiores levantam exceções tipadas (`AgentPipelineError` e derivadas); **só o orquestrador captura** e traduz em `status`. Erros recuperáveis (SQL rejeitado, erro do SQLite, saída inválida do agente) disparam retry com correção, até 3 tentativas no total. `sem_resultados` é status, não erro.
- **Formatador só formata; `latex_validator` só valida.** São passos separados no orquestrador. LaTeX inválido nunca derruba a resposta: o parágrafo vai para um bloco de código e o aviso entra no `trace`.
- **Banco não é decoração:** o texto do formatador deve vir das linhas reais devolvidas pelo SQL, nunca de texto fixo.

## Convenções

- Idioma: interface, dados do seed e mensagens ao aluno em **português do Brasil**. Nomes de tabela seguem `Topicos_Algebra`, `Exercicios`, `Resolucoes`.
- Python 3.10 (type hints modernos, mas sem recursos 3.11+). Contratos entre camadas em Pydantic (`models.py`), nunca dicts soltos.
- Dependências de runtime apenas `streamlit` e `pydantic`; `sqlite3` da stdlib. Não adicionar bibliotecas sem necessidade clara (validadores de SQL e LaTeX são propositalmente implementados à mão).
- LaTeX do seed precisa ser válido e renderizar no Streamlit (`$...$` / `$$...$$`).
- Banco em `data/edu.db` (ancorado na pasta do projeto via `DEFAULT_DB_PATH`, não no cwd), criado e populado automaticamente na primeira execução; não versionar o arquivo.
- Testes enxutos e focados em arquitetura, com `FakeLLMClient` no lugar das camadas vizinhas. Antes de dizer que algo está pronto, rode `pytest` e a demo.
