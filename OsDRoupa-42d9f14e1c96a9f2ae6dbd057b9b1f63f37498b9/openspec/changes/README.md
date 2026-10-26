# Índice de Changes — OpenSpec OSDroupa

## Estado

A única change ativa é [`023-consolidacao-geral-do-projeto/`](./023-consolidacao-geral-do-projeto/). Ela reúne os requisitos, decisões e pendências das changes anteriores em módulos. A consolidação documental não marca automaticamente como prontas as integrações externas nem os fluxos que ainda não foram exercitados.

As tarefas não concluídas foram transferidas para [`023-consolidacao-geral-do-projeto/tasks.md`](./023-consolidacao-geral-do-projeto/tasks.md). As 19 pastas originais estão preservadas em [`archive/README.md`](./archive/README.md), incluindo suas propostas, designs, especificações e marcações de tarefas.

## Diretrizes de execução

- Xano é o backend exigido para a entrega; SQLite permanece como alternativa local de desenvolvimento.
- Mercado Pago é o fluxo de pagamento atual. Referências Asaas antigas são histórico e não devem ser reativadas.
- Uma tarefa marcada como concluída só representa o que foi validado na origem. Testes de sandbox, conta, publicação, e-mail ou hardware continuam pendentes quando a lista consolidada os mantém abertos.
- Ao concluir a Change 023, revisar os requisitos e promover para `openspec/specs/` somente o comportamento implementado e validado.

## Estrutura da change ativa

```text
023-consolidacao-geral-do-projeto/
├── proposal.md
├── design.md
├── design/modules/      # decisões técnicas preservadas por domínio
├── specs/               # requisitos/cenários das changes incorporadas
└── tasks.md             # pendências abertas consolidadas
```

Changes históricas anteriores a esta organização ficam em `archive/`. As changes 018 e 019 já estavam arquivadas antes da consolidação.