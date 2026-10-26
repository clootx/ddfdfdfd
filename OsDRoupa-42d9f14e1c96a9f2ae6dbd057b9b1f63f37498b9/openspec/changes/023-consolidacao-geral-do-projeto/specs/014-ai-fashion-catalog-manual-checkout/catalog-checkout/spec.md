# Especificação — Catálogo demonstrativo e pedido sem gateway

## RF-CAT-01: Identificar produtos demonstrativos

A loja deve identificar produtos criados para demonstração. O servidor deve impedir que esses produtos sejam cobrados pelo checkout PIX.

### Cenário: mostrar produto de demonstração
- **Dado** que o catálogo contém um produto com `demonstracao=true`
- **Quando** a loja ou o detalhe do produto é exibido
- **Então** a interface mostra que é demonstrativo e não o apresenta como estoque disponível

### Cenário: bloquear PIX para item demonstrativo
- **Dado** que o carrinho contém um produto demonstrativo
- **Quando** o cliente envia o checkout PIX diretamente ao Xano
- **Então** o Xano recusa a solicitação sem criar cobrança ou pedido PIX

## RF-CHECKOUT-01: Registrar pedido demonstrativo sem cobrança

O endpoint autenticado deve aceitar somente produtos demonstrativos sob encomenda, validar o endereço do cliente e recalcular os preços no Xano.

### Cenário: enviar pedido para confirmação da loja
- **Dado** que uma conta autenticada possui um endereço próprio e o carrinho contém produtos demonstrativos válidos
- **Quando** envia o pedido com chave de idempotência
- **Então** o Xano registra PEDIDO e ITEM em uma transação
- **E** define `pagamento_status` como `Aguardando confirmação da loja`
- **E** não chama Asaas, não cria TRANSACAO e não marca pagamento como confirmado

### Cenário: recusar endereço de outra conta ou produto real
- **Dado** que o endereço não pertence à sessão atual ou que um item não é demonstrativo sob encomenda
- **Quando** o cliente tenta enviar o pedido demonstrativo
- **Então** o Xano recusa sem gravar pedido ou itens

### Cenário: repetir pedido
- **Dado** que o mesmo cliente repete a chave com endereço e itens idênticos
- **Quando** envia novamente a solicitação
- **Então** recebe o pedido existente sem duplicar pedido ou itens
- **Mas** o Xano recusa a mesma chave com itens ou endereço diferentes
