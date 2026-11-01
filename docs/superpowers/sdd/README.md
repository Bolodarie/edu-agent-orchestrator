# Como o plano foi executado (subagent-driven)

Registro do fluxo `superpowers:subagent-driven-development` usado para implementar
`docs/superpowers/plans/2026-10-31-edu-agent-orchestrator.md`.

## O que está aqui

- `ledger.md` — o livro-razão da execução: tabela de checagem de conflitos do plano antes de começar,
  cada tarefa com commits, achados das revisões, rodadas de correção, itens menores adiados
  e todas as decisões (`Ruling:`) tomadas pelo controlador.
- `tasks/task-N-brief.md` — o texto exato que cada implementador recebeu (trecho do plano).
- `tasks/task-N-report.md` — o relatório de cada implementador (o que fez, evidência TDD vermelho/verde,
  rodadas de correção acrescentadas ao fim).
- `final-fix-report.md` — relatório da onda de correção após a revisão final do branch.
- Os arquivos de diff de revisão (`review-*.diff`) não foram copiados: são reproduzíveis com `git diff`
  a partir dos SHAs citados no ledger.

## O fluxo

1. **Preparação.** Branch `feat/poc-implementation` a partir da `main`; ledger criado; varredura do plano
   por conflitos (3 ambiguidades resolvidas por decisão registrada antes da Task 1).
2. **Por tarefa:** um implementador novo (subagente, contexto isolado, só o brief da tarefa) faz TDD e
   commita → um revisor novo (spec + qualidade) lê o diff → se houver achado crítico/importante, o
   implementador original é retomado com os achados literais (rodadas 1–3; 4–5 trocariam por um modelo mais forte)
   → um re-review com escopo restrito verifica só as correções → tarefa marcada como completa no ledger.
   Achados menores vão para o ledger como adiados e são triados na revisão final.
3. **Paralelismo (pedido do usuário: até 3 agentes por vez).** Tarefas independentes rodaram em paralelo,
   cada uma num `git worktree` próprio com branch própria, mescladas na branch de feature após aprovação:
   `[T2,T3] → [T4,T5] → [T6] → [T7,T8] → T9 → T10`. Revisões também contam para o limite de 3.
4. **Revisão final do branch inteiro** (modelo mais capaz): veredito "com correções"; uma única onda de correção
   (4 achados importantes + ajustes baratos) e um re-review com escopo restrito, que fechou limpo.

## Modelos usados

Implementadores e revisores de tarefa: Sonnet · re-reviews pequenos: Haiku · revisão da Task 9 (integração): Opus ·
revisão final do branch: o modelo mais capaz disponível.

## O que as revisões pegaram (exemplos reais)

- Task 2: `strip()` quebrava Markdown quando um parágrafo inválido encostava numa cerca de código — e a correção
  introduziu uma regressão com indentação, pega no re-review.
- Task 3: `LIMIT` com dígitos Unicode ou gigante vazava `ValueError` em vez de `SQLRejeitadoError`.
- Task 7: regex de cercas duplicada em dois agentes → movida para `llm.strip_code_fences`.
- Revisão final: espaços não-ASCII (NBSP) burlavam o teto de `LIMIT` no validador de SQL; exceções fora do
  pipeline escapavam de `handle()`; o teste do modo somente leitura não exercitava o código de verdade.
