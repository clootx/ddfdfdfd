# Design Técnico — [ID-da-change]-[nome-da-change]

## Visão Geral da Arquitetura
[Diagrama textual ou explicação de como a solução técnica se integra na arquitetura global (Reflex + Xano)]

## Contratos de API (Xano)
- **[MÉTODO] `/endpoint`**
  - Headers: `Authorization: Bearer <token>`
  - Payload: `{ ... }`
  - Resposta de Sucesso: `200 OK { ... }`
  - Tratamento de Erros: `400 Bad Request`, `401 Unauthorized`

## Modelo de Estado e UI (Reflex)
- **Estado (`rx.State`):** [variáveis de estado e manipuladores de eventos]
- **Componentes de UI:** [estruturas de tela, botões, modais, formulários]

## Decisões Arquiteturais e Integridade
1. [Decisão técnica 1 e sua justificativa]
2. [Decisão técnica 2 e como preserva a integridade dos dados]
