# Design — 008-orders-checkout-payments

## Regras de segurança

- Reflex envia apenas `endereco_id`, IDs de produto, quantidades e chave de idempotência. A forma inicial de pagamento é fixa em `PIX`.
- Xano identifica o cliente por `$auth.id`, valida propriedade do endereço, recarrega produtos e calcula o total.
- Checkout nunca usa CRUD público de `PEDIDO`, `ITEM` ou `TRANSACAO`.
- Repetir a chave de idempotência retorna o mesmo pedido; chave repetida com conteúdo diferente deve ser recusada.
- Cobrança permanece pendente até um webhook Asaas autenticado e deduplicado confirmar pagamento.

## Modelo local planejado

- `PEDIDO.endereco_id`: relação anulável com `ENDERECO`.
- `PEDIDO.chave_idempotencia`: chave de tentativa única por cliente.
- `TRANSACAO.pedido_id`: relação anulável com `PEDIDO`.
- Índice único composto em `PEDIDO(cliente_id, chave_idempotencia)`.
- `TRANSACAO.pedido_id` é único para representar uma cobrança ativa por pedido.
- `EVENTO_ASAAS.event_id` é único para deduplicar entregas de webhook; o evento guarda apenas referência, status de processamento e erro resumido.

As alterações em `xano/table` são fontes locais. Elas não alteram o banco remoto até importação e migração pelo workspace Xano.

## Contratos Xano

| Operação | Rota | Acesso | Contrato esperado |
|---|---|---|---|
| Checkout | `POST /checkoutPedido` | `auth=user` | `{endereco_id, tipo:"PIX", itens:[{produto_id,qtd}], chave_idempotencia}` → pedido, itens, transação e instrução PIX |
| Histórico | `GET /meusPedidos` | `auth=user` | Pedidos pertencentes ao cliente de `$auth.id` |
| Detalhe | `GET /meuPedido/{pedido_id}` | `auth=user` | Pedido e itens, somente se pertencer ao cliente |
| Webhook | `POST /asaasWebhook` | segredo de webhook | Validar origem, deduplicar evento e atualizar transação e pedido |

O histórico, o detalhe e os schemas locais estão em `xano/api/panela_de_barro` e `xano/table`. Checkout e webhook ainda precisam de implementação e validação no workspace antes de serem ativados.

## Fluxo da interface

1. `/checkout` valida sessão, carrega endereços e lê a sacola persistida.
2. Cliente escolhe endereço; Reflex envia IDs e quantidades junto com chave persistida, cuja impressão digital inclui endereço e itens. A interface bloqueia linhas antigas sem categoria de moda, sem apagar a sacola.
3. Xano valida estoque/endereço e recalcula valores; só então cria pedido e cobrança PIX.
4. Reflex exibe QR/copia e cola em estado pendente e limpa a sacola após resposta válida.
5. `/pedidos` e `/pedido?id=` consultam endpoints privados; o webhook confirma o pagamento.

## Falhas e publicação

- Sem endereço ou sacola válida, checkout não envia requisição.
- Os endpoints locais de endereço exigem Bearer e derivam o cliente de `$auth.id`. Importar e validar essas fontes antes de depender do fluxo em ambiente remoto.
- Endpoint Xano ausente, sessão inválida e falha de rede mostram erro explícito; falha de rede preserva a chave para repetir sem duplicar.
- O frontend não afirma que o pedido foi criado quando o Xano retorna 404 ou erro.
- A chave da API Asaas fica em segredo de ambiente Xano; nunca em tabela pública, entrada ou código Reflex. O pedido usa referência estável enviada ao Asaas e, diante de timeout ambíguo, a rotina consulta a cobrança existente antes de tentar criar outra.
- O segredo do webhook é separado da chave API e validado no header `asaas-access-token`. Deduplicar pelo ID imutável do evento antes de alterar pedido/transação.
- Antes da publicação: revisar rollback/compensação se Asaas falhar após criação do pedido, eventos/status aceitos, política de estoque e catálogo de roupas.

## Verificação

- Compilar e gerar build Reflex; confirmar as três rotas.
- No workspace Xano, verificar propriedade do endereço, preço/estoque recalculados, idempotência, isolamento do histórico, resposta PIX e webhook.
- Não criar cobrança de produção nem marcar pagamento como concluído sem evento autenticado.
