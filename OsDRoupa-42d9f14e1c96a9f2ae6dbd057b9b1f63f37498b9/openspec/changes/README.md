# Índice de Changes — OpenSpec OSDroupa

## Estado

Changes ativas:

| Change | Situação | Resumo |
|---|---|---|
| [`023-consolidacao-geral-do-projeto/`](./023-consolidacao-geral-do-projeto/) | Em validação | Consolidação documental e pendências Xano |
| [`024-contexto-climatico/`](./024-contexto-climatico/) | Implementada; validação no navegador pendente | Clima real (Open-Meteo) a partir da cidade do endereço padrão |
| [`025-motor-looks-ia/`](./025-motor-looks-ia/) | Implementada; provedor trocado pela 029; navegador pendente | Looks completos com justificativa no servidor Reflex |
| [`026-avaliacao-looks/`](./026-avaliacao-looks/) | Implementada; provedor trocado pela 029; navegador pendente | Notas por critério, problemas e trocas aplicáveis para looks da IA e manuais |
| [`027-visualizacao-looks/`](./027-visualizacao-looks/) | Implementada; imagem paga desligada por padrão (029) | Quadro com fotos reais e imagem editorial pela API Gemini do Google |
| [`028-feed-inspiracao/`](./028-feed-inspiracao/) | Implementada no SQLite; Xano em rascunho; navegador pendente | Inspirações salvas, feed com filtros e publicação anônima moderada |
| [`029-estilista-gemini/`](./029-estilista-gemini/) | Etapas 3 a 6 implementadas (provedor, limites, plano B, looks mais ricos); Xano e chamada real pendentes | Estilista no Google Gemini (plano gratuito), camada de provedor, imagens desligadas |
| [`030-perfil-estilo-ia/`](./030-perfil-estilo-ia/) | Implementada no SQLite; Xano em rascunho; navegador pendente | Perfil de estilo para a IA, feedback 👍/👎 e opção de desligar |

Change planejada, ainda sem pasta: 031-publicacoes-usuarios (opcional).

A change 023 reúne os requisitos, decisões e pendências das changes anteriores em módulos. A consolidação documental não marca automaticamente como prontas as integrações externas nem os fluxos que ainda não foram exercitados.

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