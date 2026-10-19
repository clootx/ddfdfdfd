# Tarefas — 008-orders-checkout-payments

## Status: IMPLEMENTAÇÃO PARCIAL; XANO E VALIDAÇÃO VISUAL PENDENTES

### OpenSpec
- [x] Registrar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.
- [x] Limitar a primeira forma de pagamento a PIX conforme os estados existentes.

### Backend Xano local
- [x] Adicionar fontes locais para endereço e chave de idempotência em `PEDIDO` e vínculo `TRANSACAO.pedido_id`.
- [x] Restringir rotas CRUD genéricas de pedido, item, transação e cliente a administradores.
- [x] Desativar as rotas Asaas legadas que aceitavam valor livre ou token de autenticação pela entrada.
- [x] Modelar uma cobrança por pedido e criar fonte `EVENTO_ASAAS` com ID de webhook único.
- [x] Tornar consulta de endereços autenticada e retirar token da query no contrato local.
- [x] Criar consultas privadas locais para histórico e detalhe do cliente.
- [ ] Implementar `POST /checkoutPedido` com validação, recálculo, estoque, idempotência e Asaas PIX.
- [ ] Implementar webhook Asaas autenticado, deduplicado e responsável pela confirmação.
- [ ] Importar fontes, migrar schema e validar os contratos no workspace Xano.

### Frontend Reflex
- [x] Criar `/checkout`, `/pedidos` e `/pedido?id={id}`.
- [x] Enviar somente IDs/quantidades e preservar chave em falha de rede.
- [x] Incluir endereço e itens na impressão digital da chave de idempotência.
- [x] Validar ID da cobrança e instrução PIX antes de limpar a sacola ou mostrar sucesso.
- [x] Exibir instrução PIX apenas após resposta válida do checkout.
- [ ] Validar estados visuais e formatos reais das respostas no navegador.

### Verificação e ativação
- [x] Executar `py_compile`, compilação Reflex e build de produção; respostas HTTP 200 nas novas rotas e 404 em `/dashboard`.
- [x] Validar sintaxe Xano dos schemas e endpoints locais alterados.
- [ ] Exercitar propriedade do endereço, estoque, idempotência, isolamento entre clientes e erros Asaas no sandbox.
- [ ] Confirmar que preço do navegador não altera total e pagamento só confirma por webhook.
- [ ] Cadastrar roupas no catálogo Xano e remover os 15 registros atuais de alimentos/bebidas antes de habilitar pedidos reais.
