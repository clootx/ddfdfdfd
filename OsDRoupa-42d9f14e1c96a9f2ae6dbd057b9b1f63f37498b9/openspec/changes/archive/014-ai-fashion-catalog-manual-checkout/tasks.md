# Tarefas — 014-ai-fashion-catalog-manual-checkout

## Status: IMPLEMENTADA COM PENDÊNCIAS DE CONFIGURAÇÃO

### OpenSpec
- [x] Registrar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.

### Xano
- [x] Adicionar flag `demonstracao` ao produto e publicar schema.
- [x] Implementar pedido demonstrativo autenticado, idempotente e sem transação financeira.
- [x] Bloquear produtos demonstrativos no endpoint PIX.
- [x] Preparar catálogo aditivo com produtos gerados por IA e pré-visualizar os records.
- [x] Publicar os scripts e os novos records após revisar a prévia na branch `v1`.

### Reflex
- [x] Exibir selo e aviso de produto demonstrativo.
- [x] Enviar carrinho demonstrativo ao endpoint sem gateway e mostrar estado pendente.
- [x] Preservar o fluxo PIX para produtos reais e recusar carrinho misto.

### Verificação
- [x] Validar XanoScript e prévias de schema, endpoints e records.
- [x] Executar `py_compile` e `reflex compile --dry`.
- [x] Validar HTTP 200 em loja, produto e checkout.
- [ ] Exercitar pedido autenticado com conta e endereço de teste no workspace.
- [ ] Gerar e publicar fotos dos produtos; a nova tentativa em 2026-10-23 retornou `429 credit_balance_exhausted` (`You have no credits remaining`). O catálogo continua usando ilustrações SVG locais até haver créditos disponíveis.
