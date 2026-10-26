# Especificação — Pedidos, Checkout e Pagamentos

## RF-ORD-01: Checkout autenticado

O checkout exige sessão válida, endereço pertencente ao cliente e ao menos um item. O navegador não define preço, total, cliente nem status.

### Cenário: compra validada
- **Dado** que a sessão, o endereço e o estoque foram validados no Xano
- **Quando** a pessoa confirma a compra
- **Então** o Xano cria pedido e itens com preços e total calculados no servidor

### Cenário: endereço de outra conta
- **Dado** que o endereço não pertence ao cliente autenticado
- **Quando** a pessoa envia o checkout
- **Então** o Xano recusa a operação antes de criar cobrança

## RF-ORD-02: Integridade e idempotência

Pedido, itens e transação devem estar relacionados no backend. Repetir a mesma chave com o mesmo conteúdo retorna o mesmo resultado; reutilizá-la para conteúdo diferente é recusado.

### Cenário: estoque insuficiente
- **Dado** que a quantidade pedida excede a disponibilidade atual
- **Quando** o Xano valida o checkout
- **Então** informa os itens indisponíveis sem gerar cobrança

O navegador inclui endereço e itens na impressão digital da chave. Alterar qualquer um deles inicia uma chave nova; repetir a mesma tentativa mantém a chave.

## RF-ORD-03: Pagamento PIX

O checkout inicial oferece PIX no Asaas sandbox. A cobrança fica pendente após criação; somente um webhook autenticado pode confirmar o pagamento.

O checkout só exibe sucesso e limpa a sacola depois de receber pedido, ID da cobrança e instrução PIX válidos. Timeout ambíguo preserva a chave e exige consulta da referência externa estável antes de repetir criação da cobrança.

## RF-ORD-04: Histórico privado

`/pedidos` e `/pedido?id={id}` consultam dados autenticados e não revelam pedidos pertencentes a outra conta.

## RF-ORD-05: Recuperação

Falha no Xano ou Asaas deve mostrar mensagem clara, preservar a chave de idempotência quando apropriado e nunca exibir confirmação de pagamento sem confirmação do backend.

### Cenário: resposta de checkout incompleta
- **Dado** que a resposta não contém ID da cobrança ou instrução PIX
- **Quando** o frontend recebe a resposta
- **Então** mantém a sacola e a chave de tentativa e não apresenta sucesso
