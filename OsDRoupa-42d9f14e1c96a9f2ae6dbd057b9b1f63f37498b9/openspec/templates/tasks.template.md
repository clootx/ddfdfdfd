# Tarefas de Implementação — [ID-da-change]-[nome-da-change]

Este checklist guia a execução durante o workflow `Apply`.

## Fase 1 — Modelagem e Backend (Xano)
- [ ] 1.1 Configurar/ajustar tabelas ou campos necessários no Xano.
- [ ] 1.2 Implementar e validar endpoints no Xano com autenticação e validações.
- [ ] 1.3 Testar endpoints com dados de teste válidos e inválidos.

## Fase 2 — Integração e Serviços (Python)
- [ ] 2.1 Criar ou atualizar funções de chamada de API em `services/`.
- [ ] 2.2 Tratar erros de rede, status codes e serialização de dados.

## Fase 3 — Estado da Aplicação (Reflex State)
- [ ] 3.1 Declarar variáveis de estado (`rx.State`) e tipos de dados.
- [ ] 3.2 Implementar event handlers para carregar, enviar e validar dados.

## Fase 4 — Interface do Usuário (Reflex UI)
- [ ] 4.1 Construir ou atualizar componentes visuais e páginas.
- [ ] 4.2 Adicionar feedback visual (carregamento, sucesso, erro).

## Fase 5 — Verificação e Testes (Verify)
- [ ] 5.1 Executar os cenários de teste descritos na especificação (`specs/`).
- [ ] 5.2 Validar que os critérios de aceitação foram cumpridos sem regressão.
