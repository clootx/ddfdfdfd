# Especificação consolidada — Pedidos e Pagamentos

## RF-ORD-01: Checkout autenticado

Checkout exige sessão válida e endereço pertencente ao cliente. O frontend envia IDs e quantidades; Xano determina proprietário, disponibilidade, preços, total e status.

## RF-ORD-02: Pedido consistente

Pedido guarda cliente e endereço; itens guardam produto, quantidade, preço unitário e subtotal calculados no servidor. A transação financeira referencia o pedido.

## RF-ORD-03: Pagamento PIX

O pagamento inicial usa PIX no Asaas sandbox. A cobrança fica pendente até webhook autenticado e deduplicado confirmar a liquidação.

## RF-ORD-04: Histórico privado

Lista e detalhe são filtrados no backend pelo cliente associado ao token, inclusive quando um ID de pedido é informado diretamente.

## RF-ORD-05: Idempotência e falhas

Repetições da mesma tentativa não criam cobranças duplicadas. A impressão digital inclui endereço e itens. Erros de validação ocorrem antes da cobrança; falhas posteriores não simulam pagamento confirmado.

O checkout exige uma resposta com pedido, cobrança e instrução PIX antes de limpar a sacola. Para timeout ambíguo, consulta a referência externa estável antes de nova tentativa. Eventos Asaas são deduplicados por ID imutável e autenticados pelo segredo separado enviado no header `asaas-access-token`.
