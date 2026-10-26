# Design — 008-orders-checkout-payments

## Regras de segurança

> Atualização: a Change 020 substitui o desenho Asaas desta proposta. Os rascunhos XanoScript locais foram bloqueados (endpoints já publicados remotamente devem ser desativados no painel); no backend SQLite, a venda real usa Mercado Pago Orders e webhook assinado. O caminho Xano Mercado Pago ainda precisa ser portado e publicado.

- Reflex envia apenas endereco_id, IDs de produto, quantidades e chave de idempotência. A forma inicial de pagamento é fixa em PIX.
- Xano identifica o cliente por $auth.id, valida propriedade do endereço, recarrega produtos e calcula o total.
- Checkout nunca usa CRUD público de PEDIDO, ITEM ou TRANSACAO.
- Repetir a chave de idempotência retorna o mesmo pedido; chave repetida com conteúdo diferente deve ser recusada.
- Cobrança permanece pendente até webhook Asaas autenticado e deduplicado confirmar pagamento.

## Modelo local planejado

- PEDIDO.endereco_id: relação anulável com ENDERECO.
- PEDIDO.chave_idempotencia: chave de tentativa única por cliente.
- PEDIDO.assinatura_checkout: impressão digital privada do endereço e dos itens.
- TRANSACAO.pedido_id: relação anulável com PEDIDO.
- TRANSACAO.status_gateway, pago_confirmado e confirmado_em: estado auditável da cobrança.
- Índice único composto em PEDIDO(cliente_id, chave_idempotencia).
- EVENTO_ASAAS.event_id é único para deduplicar entregas de webhook; o evento guarda referência, estado de processamento e erro resumido.

As alterações em xano/table são fontes locais. Elas não alteram o banco remoto até importação e migração pelo workspace Xano.

## Contratos Xano

| Operação | Rota | Acesso | Contrato esperado |
|---|---|---|---|
| Checkout | POST /checkoutPedido | auth=user | {endereco_id, tipo:"PIX", itens:[{produto_id,qtd}], chave_idempotencia} → pedido e instrução PIX recalculados no servidor |
| Histórico | GET /meusPedidos | auth=user | Pedidos pertencentes ao cliente de $auth.id, com estado do pagamento |
| Detalhe | GET /meuPedido/{pedido_id} | auth=user | Pedido e itens, somente se pertencer ao cliente |
| Webhook | POST /asaasWebhook | segredo de webhook | Validar origem, deduplicar evento e atualizar transação e pedido |

Os rascunhos locais de checkout e webhook já existem em xano/api/panela_de_barro; foram aprovados pelo parser Xano local. Ainda precisam ser importados, revisados e exercitados no workspace antes de qualquer ativação.

## Fluxo da interface

1. /checkout valida sessão, carrega endereços e lê a sacola persistida.
2. Cliente escolhe endereço; Reflex envia IDs e quantidades junto com chave persistida, cuja impressão digital inclui endereço e itens. A interface bloqueia linhas antigas sem categoria de moda sem apagar a sacola.
3. Xano valida estoque/endereço e recalcula valores; só então cria pedido e cobrança PIX.
4. Reflex exibe QR/copia e cola em estado pendente e limpa a sacola após resposta válida.
5. /pedidos e /pedido?id= consultam endpoints privados; somente o webhook autenticado confirma pagamento.

## Falhas e publicação

- Sem endereço ou sacola válida, checkout não envia requisição.
- Os endpoints locais de endereço exigem Bearer e derivam o cliente de $auth.id. Importar e validar essas fontes antes de depender do fluxo em ambiente remoto.
- Endpoint Xano ausente, sessão inválida e falha de rede mostram erro explícito; falha de rede preserva a chave para repetir sem duplicar.
- A API Asaas fica em segredo de ambiente Xano; nunca em tabela pública, entrada ou código Reflex. O pedido usa referência estável e, diante de timeout ambíguo, consulta a cobrança existente antes de tentar criar outra.
- O segredo do webhook é separado da chave API e validado no header asaas-access-token. Deduplicar pelo ID imutável antes de alterar pedido/transação.
- Política de expiração/liberação do estoque reservado precisa ser definida e validada antes da publicação. Produtos atuais remotos também precisam ser substituídos/classificados como moda.

## Verificação

- Compilar e gerar build Reflex; confirmar as rotas locais.
- No workspace Xano, verificar propriedade do endereço, preço/estoque recalculados, idempotência, isolamento do histórico, resposta PIX e webhook.
- Não criar cobranças de produção nem marcar pagamento como concluído sem evento autenticado.
