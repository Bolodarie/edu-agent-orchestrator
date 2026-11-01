# Edu Agent Orchestrator — Design

Data: 2026-10-31

## 1. Intenção e porquê

Prova de conceito (PoC) de uma **arquitetura multi-agente integrada a um banco de dados**, 100% Python + Streamlit. O domínio é um assistente educacional para alunos de um cursinho popular de álgebra (o autor é professor voluntário): o aluno pergunta no chat e o sistema busca e estrutura exercícios, resumos teóricos e resoluções.

**O propósito real é portfólio.** O que o projeto precisa demonstrar é domínio sobre desenho de arquitetura e separação de responsabilidades entre front, back e dados. O código não pode ser monolítico, e as fronteiras entre camadas devem ser visíveis e verificáveis. Não há preocupação com evolução futura do produto: nada de configuração sofisticada, múltiplos provedores de LLM ou persistência de conversa.

## 2. Objetivos, não-objetivos, anti-objetivos

**Objetivos**
- Camadas com responsabilidade única e dependências em uma só direção.
- Contratos tipados entre camadas.
- Pipeline de agentes completo e executável de ponta a ponta, com um LLM simulado (mock), pronto para trocar por um LLM real mudando uma linha de montagem.
- Segurança do SQL gerado por LLM tratada como preocupação de primeira classe.
- Fluxo de dados visível na demo (expander com o rastro de cada resposta).
- Cada camada testável isoladamente.

**Não-objetivos**
- Chamar um LLM real (nenhum SDK de LLM entra nas dependências).
- Memória/contexto de conversa entre turnos.
- Autenticação, multiusuário, deploy, observabilidade externa.
- Interface de testes do Streamlit, métricas de cobertura.

**Anti-objetivos (falha mesmo que "funcione")**
- `app.py` importando `database` ou `agents`.
- Agentes dependendo da camada de dados.
- Resposta do formatador com texto fixo ignorando os dados do banco (o banco viraria decoração).
- SQL vindo da LLM executado sem validação e em conexão com permissão de escrita.

## 3. Restrições

- Python 3.10 (versão da máquina), Streamlit 1.63, Pydantic 2.12. Dependências de runtime: `streamlit`, `pydantic`. Dev: `pytest`.
- SQLite via biblioteca padrão `sqlite3`.
- Idioma da interface, dos dados e das mensagens ao aluno: **português do Brasil**. Identificadores de domínio seguem os nomes pedidos (`Topicos_Algebra`, `Exercicios`, `Resolucoes`).
- A pasta do projeto é um repositório git (remote `origin` = github `Bolodarie/edu-agent-orchestrator`).

## 4. Arquitetura

### 4.1 Regra de dependência

```
app.py  ──►  orchestrator.py  ──►  agents/*  ──►  llm.py
                    │
                    └──────────►  database.py
```

- `app.py` conhece só `Orchestrator`, `OrchestratorResponse` e `build_orchestrator()` (todos de `orchestrator.py`/`models.py`).
- `agents/` conhece `llm.py`, `models.py`, `exceptions.py`. **Nunca** `database`.
- `database.py` não conhece agentes nem LLM.
- O orquestrador é a única peça que enxerga agentes e banco juntos: é ele quem leva o SQL do Agente de Consulta até o banco.

### 4.2 Estrutura de arquivos

```
app.py                 # FRONT: captura input, renderiza OrchestratorResponse
orchestrator.py        # BACK: fluxo, retry, tradução de erros, build_orchestrator()
database.py            # DATA: schema, seed, validador de SQL, execução somente leitura
models.py              # contratos tipados (Pydantic)
exceptions.py          # AgentPipelineError e derivadas
llm.py                 # LLMClient (Protocol) + MockLLMClient
latex_validator.py     # função pura de validação de LaTeX
agents/
  router.py            # Agente Roteador
  query.py             # Agente de Consulta
  formatter.py         # Agente Formatador
tests/
README.md              # inclui diagrama das camadas
requirements.txt
data/edu.db            # criado e populado na primeira execução
```

### 4.3 Fluxo de uma requisição

1. `app.py` recebe o texto do aluno e chama `orchestrator.handle(texto)`.
2. **Roteador** classifica a intenção → `RouterResult(intent, confidence)`. Se `intent == FORA_DO_ESCOPO`, o orquestrador devolve `status="fora_do_escopo"` com mensagem educada, sem tocar no banco.
3. **Agente de Consulta** recebe a intenção, o texto original e a descrição do schema, e devolve uma string SQL.
4. O orquestrador chama `database.execute_readonly(sql)`. O banco valida e executa. Em erro recuperável (`SQLRejeitadoError` ou erro de execução do SQLite) o orquestrador chama o Agente de Consulta de novo, passando o SQL anterior e a mensagem de erro, até **3 tentativas no total** (1 inicial + 2 correções). Esgotadas as tentativas: `status="erro"`.
5. Zero linhas devolvidas → `status="sem_resultados"` (não é erro, não há retry).
6. **Formatador** recebe intenção + linhas reais do banco e devolve Markdown com LaTeX.
7. `latex_validator` confere o texto formatado. Trechos inválidos são movidos para um bloco de código e um aviso entra no `trace`; a resposta nunca é derrubada por isso.
8. O orquestrador devolve `OrchestratorResponse`. `app.py` renderiza.

### 4.4 Contratos (`models.py`)

- `Intent` — `Enum` fechado: `BUSCAR_EXERCICIOS`, `BUSCAR_RESUMO`, `BUSCAR_RESOLUCAO`, `FORA_DO_ESCOPO`.
- `RouterResult` — `intent: Intent`, `confidence: float` (0–1; vai ao `trace`, não decide nada).
- `QueryAttempt` — `sql`, `error: str | None`, `row_count: int | None`.
- `Trace` — intenção e confiança, lista de `QueryAttempt`, avisos (ex.: LaTeX inválido), tempo por etapa.
- `OrchestratorResponse` — `text: str`, `status: Literal["ok","fora_do_escopo","sem_resultados","erro"]`, `trace: Trace`.

### 4.5 Camada de agentes

Cada agente recebe um `LLMClient` por injeção no construtor, monta um prompt real (system + user) e interpreta a saída.

- **Roteador:** pede a intenção; valida contra o `Enum`. Valor fora do conjunto → `IntencaoDesconhecidaError` (não recuperável).
- **Consulta:** só transforma intenção em SQL. Não conhece o banco (recebe a descrição do schema como texto). Aceita opcionalmente o SQL e o erro da tentativa anterior para se corrigir.
- **Formatador:** só formata. Recebe as linhas reais e produz Markdown/LaTeX. Não valida LaTeX (isso é do `latex_validator`).

### 4.6 `LLMClient` e mock (`llm.py`)

- `LLMClient` é um `Protocol` com um método de completar (system + user → `str`).
- `MockLLMClient` varia a resposta por regras simples de palavra-chave, escondidas dentro dele; os agentes não sabem que isso existe:
  - "exercício"/tópico mencionado → `BUSCAR_EXERCICIOS` e SQL filtrando o tópico;
  - "resumo"/"teoria" → `BUSCAR_RESUMO`;
  - "resolução"/"resolver" (e variações como "resolva"/"resolve") → `BUSCAR_RESOLUCAO`;
  - qualquer outra coisa → `FORA_DO_ESCOPO`.
  - O mock do formatador monta o Markdown a partir dos dados reais presentes no prompt.
- **Gancho de demo do retry (decisão do designer):** se o texto do aluno contiver "teste retry", o mock devolve SQL inválido na primeira tentativa e, ao ver o erro no prompt da segunda, devolve o SQL correto.
- Trocar por LLM real = escrever uma classe que implemente `LLMClient` e mudá-la em `build_orchestrator()`.

### 4.7 Camada de dados (`database.py`)

Schema:

- `Topicos_Algebra(id, nome, descricao, resumo_teorico)` — `resumo_teorico` em Markdown com LaTeX.
- `Exercicios(id, topico_id → Topicos_Algebra, enunciado_latex, dificuldade)`
- `Resolucoes(id, exercicio_id → Exercicios, passo_a_passo_latex)`

Seed (**decisão do designer**): ~4 tópicos (ex.: equação do 1º grau, equação do 2º grau, sistemas lineares, fatoração), 2–3 exercícios por tópico, uma resolução por exercício. Todo LaTeX do seed precisa ser válido e renderizável pelo Streamlit.

Segurança do SQL (responsabilidade de `database.py`, independente do agente):

1. **Validador:** só `SELECT`; uma única instrução; apenas tabelas da lista permitida; `LIMIT` obrigatório. Violação → `SQLRejeitadoError`.
2. **Conexão somente leitura** (`file:...?mode=ro`) como segunda barreira independente.

O banco é criado e populado automaticamente em `data/edu.db` se não existir (usando uma conexão de escrita separada, usada só no seed).

### 4.8 Erros (`exceptions.py`)

`AgentPipelineError` (base) com derivadas: `IntencaoDesconhecidaError` (não recuperável), `SQLRejeitadoError` (recuperável), além de um erro para falha de execução do SQLite (recuperável). Camadas inferiores só levantam; **somente o orquestrador captura** e traduz para `status` + mensagem amigável ao aluno. Detalhe técnico vai no `trace`.

### 4.9 Front-end (`app.py`)

- `st.chat_input` captura; `st.chat_message` renderiza.
- Histórico em `st.session_state` **somente para redesenhar** o chat. O orquestrador é stateless: `handle(texto)`, sem histórico.
- A resposta usa `st.markdown` (que renderiza `$...$` e `$$...$$`). O `status` escolhe o estilo (normal, aviso, erro).
- O `trace` aparece em `st.expander("Como a resposta foi gerada")`: intenção e confiança, cada tentativa de SQL com seu erro, número de linhas, avisos, tempos.
- O orquestrador é criado uma vez com `@st.cache_resource` via `build_orchestrator()`.

### 4.10 Testes

`pytest`, enxutos e focados na arquitetura:

- `database`: validador rejeita `DROP`, múltiplas instruções, tabela fora da lista e query sem `LIMIT`; conexão somente leitura recusa escrita.
- `latex_validator`: casos válidos e inválidos (`$`/`$$` em pares, `{}` balanceadas, `\left/\right` e `\begin/\end` em pares).
- Agentes: cada um com um `FakeLLMClient`, sem banco.
- `orchestrator`: fluxo feliz; retry (SQL ruim e depois correto); esgotar tentativas; fora de escopo; sem resultados.
- Fronteira de camadas: falha se `app.py` importar `database`/`agents`, ou se `agents/` importar `database`.

Critério de pronto: a suíte roda e passa, e a demo funciona de ponta a ponta no Streamlit.

## 5. Decisões do usuário (resumo)

Portfólio, sem foco em evolução · `LLMClient` injetado com mock · SQL livre da LLM com validador + conexão read-only · mock com regras de palavra-chave · orquestrador devolve objeto tipado com `trace` · resumos em coluna de `Topicos_Algebra` · exceções tipadas com **retry com correção** controlado pelo orquestrador (3 tentativas) · validação determinística de LaTeX · estrutura de arquivos na raiz com `agents/` · roteador devolve só intenção (+ confiança) · orquestrador stateless · testes enxutos.

## 6. Escolhas do designer (podem ser contestadas)

- Gancho "teste retry" no mock.
- Seed de ~4 tópicos × 2–3 exercícios, em `data/edu.db`, criado na primeira execução.
- `build_orchestrator()` em `orchestrator.py`; `app.py` o chama via `@st.cache_resource`.
- Inventário concreto dos tópicos, dificuldades (ex.: fácil/média/difícil) e textos do seed.
- Formato exato do prompt de cada agente e do protocolo de saída (ex.: JSON para o roteador, SQL puro para a consulta).
- Como o validador de SQL é implementado (análise por regex/tokens da stdlib, sem dependência nova).
- Forma exata do `Trace` além dos campos listados.
- Mensagens ao aluno para cada `status`.

### 6.1 Contrato de prompts entre agentes e mock

Os prompts de usuário são montados com blocos rotulados em linhas próprias. O mock lê esses rótulos; uma LLM real os lê como texto comum.

- **Roteador:** `PERGUNTA:`. Saída esperada: JSON `{"intent": "...", "confidence": 0.0}`. JSON malformado ou intenção fora do `Enum` → `IntencaoDesconhecidaError`. Confiança baixa não muda o comportamento (só vai ao `trace`).
- **Consulta:** `PERGUNTA:`, `INTENCAO:`, `SCHEMA:` e, a partir da 2ª tentativa, `SQL_ANTERIOR:` e `ERRO_ANTERIOR:`. O agente remove cercas de código (` ``` `) da saída; se sobrar texto vazio ou sem `SELECT`, levanta `SaidaDoAgenteInvalidaError` (recuperável).
- **Formatador:** `INTENCAO:` e `DADOS:` (lista JSON de linhas, uma chave por coluna do SELECT).
- **Detecção do retry pelo mock:** a presença do bloco `ERRO_ANTERIOR:` indica 2ª tentativa ou posterior.

### 6.2 Regras do mock

- Normalização: minúsculas e sem acentos antes de comparar.
- **Precedência** quando várias regras casam: `resolu`/`resolver` → `BUSCAR_RESOLUCAO`; senão `resumo`/`teoria` → `BUSCAR_RESUMO`; senão `exercicio`/`questao`/`lista` → `BUSCAR_EXERCICIOS`; senão, só um tópico conhecido citado → `BUSCAR_EXERCICIOS`; senão `FORA_DO_ESCOPO`.
- **Tópico:** o mock tem um catálogo de nomes de tópico e apelidos (ex.: "2º grau", "segundo grau", "bhaskara") e filtra por nome via `LIKE` sobre `Topicos_Algebra.nome`. Ele **não** conhece ids do banco. Sem tópico citado, a consulta não filtra por tópico. Tópico citado que não existe no catálogo do mock resulta em filtro sem linhas → `sem_resultados`. O catálogo inclui `Logaritmo`, ausente do seed, justamente para exercitar esse caminho.
- **Gancho "teste retry":** só afeta o SQL. A classificação de intenção segue as regras acima normalmente. Na 1ª tentativa (sem `ERRO_ANTERIOR:`) o mock devolve `SELECT * FROM Exercicios` (sem `LIMIT`), que o validador rejeita com `SQLRejeitadoError`, exercitando o caminho de rejeição e retry. Na 2ª, devolve o SQL correto.

### 6.3 SQL por intenção

Todos com `LIMIT` e `JOIN` com alias, filtro opcional por tópico:

- `BUSCAR_EXERCICIOS`: `t.nome`, `e.enunciado_latex`, `e.dificuldade`; de `Exercicios e JOIN Topicos_Algebra t`; `LIMIT 5`.
- `BUSCAR_RESUMO`: `t.nome`, `t.resumo_teorico`; de `Topicos_Algebra t`; `LIMIT 3`.
- `BUSCAR_RESOLUCAO`: `t.nome`, `e.enunciado_latex`, `r.passo_a_passo_latex`; de `Resolucoes r JOIN Exercicios e JOIN Topicos_Algebra t`; `LIMIT 3`.

### 6.4 Validador de SQL

Implementado com tokenização da stdlib que respeita literais entre aspas, sem dependência nova:

- Rejeita comentários (`--`, `/* */`) fora de literais.
- Rejeita mais de uma instrução (um `;` final é tolerado).
- Primeira palavra deve ser `SELECT`. CTEs (`WITH`) são rejeitadas. Subconsultas são aceitas.
- Palavras proibidas fora de literais: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `PRAGMA`, entre outras.
- Todo identificador depois de `FROM`/`JOIN` deve estar na lista de tabelas permitidas; aliases são aceitos.
- Exige `LIMIT <inteiro>` como cláusula final no nível superior, com teto de 50.
- É uma checagem razoável para a PoC, não um parser SQL completo; a conexão somente leitura é a barreira que não depende dele.
- Erro de execução do SQLite vira `SQLExecucaoError` (recuperável).

### 6.5 Validador de LaTeX

- Analisa o texto fora de blocos de código com cercas.
- `\$` conta como `$` literal. Cifrão de moeda não é tratado (o seed não usa).
- Unidade de validação: o parágrafo (separado por linha em branco). Parágrafo com delimitador desbalanceado, chave desbalanceada ou `\left/\right`/`\begin/\end` sem par é embrulhado inteiro num bloco de código, e o aviso entra em `Trace.avisos`.

### 6.6 Fronteira de imports do `app.py`

`app.py` importa só `orchestrator` e `models` (os tipos `OrchestratorResponse` e `Trace` vêm de `models`). O teste de fronteira usa `ast` para ler os imports.

## 7. Deixado ao construtor

Nomes internos de funções, organização dos testes, detalhes de estilo do Streamlit, conteúdo do README (deve incluir diagrama das camadas e citar o limite conhecido de não ter memória de conversa).
