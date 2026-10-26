# Especificação consolidada — Pedidos e pagamentos

## RF-ORD-01: Checkout autenticado

Checkout exige sessão válida e endereço pertencente à conta. O frontend envia IDs e quantidades; o backend determina proprietário, disponibilidade, preço, total e estado.

## RF-ORD-02: Pedido consistente

O pedido guarda cliente e endereço. Itens guardam produto, quantidade, preço unitário e subtotal calculados no servidor. A transação de pagamento referencia o pedido.

## RF-ORD-03: Checkout Mercado Pago Orders

No modo SQLite, pedidos demonstrativos não cobram. Produtos marcados para venda real usam Mercado Pago Orders quando o token de acesso está configurado. O servidor reserva estoque e cria a Order com uma chave idempotente; o navegador recebe apenas a URL segura de checkout.

## RF-ORD-04: Confirmação assinada

Retornos do navegador não confirmam pagamento. O webhook Orders precisa ter assinatura válida; o backend consulta a Order com credencial privada e confere referência externa e total antes de marcar o pedido como pago. Eventos repetidos são deduplicados.

## RF-ORD-05: Histórico privado

Lista e detalhe são filtrados no backend pela conta do token, inclusive quando um ID de pedido é informado diretamente.

## RF-ORD-06: Idempotência e falhas

Repetições da mesma tentativa não devem criar pedidos ou cobranças duplicadas. A impressão digital inclui endereço e itens. Erros de validação ocorrem antes de criar cobrança; falhas posteriores não simulam pagamento confirmado. Reservas pendentes expiram e devolvem o estoque.

## Limite do modo Xano

Os rascunhos XanoScript legados que usavam Asaas estão bloqueados no repositório. O app impede checkout real no modo Xano; um endpoint já publicado no workspace remoto precisa ser desativado no painel. A implementação Mercado Pago está no backend SQLite local; o modo Xano só poderá cobrar após portar, publicar e validar Orders e webhook no workspace.
