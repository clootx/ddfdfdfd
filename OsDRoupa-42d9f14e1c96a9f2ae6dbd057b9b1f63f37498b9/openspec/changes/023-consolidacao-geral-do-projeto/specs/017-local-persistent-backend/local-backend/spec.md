# Capacidade: backend local persistente

## Requisitos

### Requisito: cadastro e sessão locais

O backend DEVE criar contas com senha derivada e abrir sessões opacas com validade. O papel administrativo DEVE ser definido apenas por configuração de servidor.

#### Cenário: criação e uso de conta

- **Dado** que o backend SQLite esteja ativo
- **Quando** uma pessoa enviar cadastro válido e depois entrar com as credenciais
- **Então** os dados pessoais são persistidos e a sessão permite acessar somente dados vinculados àquela pessoa

#### Cenário: credenciais incorretas

- **Dado** um e-mail inexistente ou uma senha incorreta
- **Quando** a pessoa tentar entrar
- **Então** o servidor retorna erro genérico sem revelar qual campo está incorreto

### Requisito: isolamento de dados

O backend DEVE validar no servidor a propriedade de endereço, item, look, desafio e pedido em cada leitura e escrita autenticada.

#### Cenário: usuário consulta registro alheio

- **Dado** um registro pertencente a outra conta
- **Quando** a pessoa tentar consultar, alterar ou excluir esse registro
- **Então** a operação é negada e o registro não é alterado

### Requisito: pedido demonstrativo idempotente

O backend DEVE validar endereço, produto, quantidade e estoque, preservar uma chave de idempotência e armazenar linhas e preços como fotografia do pedido. O pedido demonstrativo NÃO DEVE criar cobrança nem ser marcado como pago.

#### Cenário: repetição da mesma tentativa

- **Dado** um carrinho e endereço válidos
- **Quando** a mesma chave de idempotência for enviada novamente
- **Então** o mesmo pedido é retornado sem duplicar pedido ou reserva de estoque

#### Cenário: pedido demonstrativo

- **Dado** itens demonstrativos disponíveis e um endereço da conta
- **Quando** a pessoa finalizar a compra
- **Então** o pedido fica pendente de confirmação, nenhum pagamento é realizado e a reserva expira se a loja não confirmar o pedido no prazo

#### Cenário: pedido confirmado mantém o estoque reservado

- **Dado** um pedido confirmado antes do fim do prazo da reserva
- **Quando** o backend liberar reservas pendentes expiradas
- **Então** o pedido confirmado mantém o status e o estoque continua reservado até cancelamento permitido ou conclusão do pedido

### Requisito: operação administrativa

O backend DEVE restringir cadastro de produtos, leitura de gestão e transição de pedido a administradores, validar transições permitidas e conciliar receitas somente de pagamentos confirmados.

#### Cenário: member tenta acessar gestão

- **Dado** uma sessão válida com papel member
- **Quando** ela solicitar um recurso administrativo
- **Então** o backend retorna acesso negado sem expor registros

#### Cenário: receita demonstrativa

- **Dado** um pedido que não possui confirmação de pagamento
- **Quando** o resumo financeiro for calculado
- **Então** o valor do pedido não é somado à receita recebida

### Requisito: integração externa explícita

O checkout local e o pareamento local DEVEM ser identificados como demonstração. Sem SMTP, a recuperação local PODE exibir um link de redefinição somente se isso estiver habilitado, identificando que nenhum e-mail foi enviado. A resposta não deve revelar se o e-mail informado pertence a uma conta.

#### Cenário: serviços externos indisponíveis

- **Dado** que SMTP, Asaas ou hardware não estejam configurados
- **Quando** a pessoa solicitar esses serviços
- **Então** a interface oferece um link local de uso único ou informa a indisponibilidade, sem alegar envio de e-mail

### Requisito: integridade de endereço e preço
O backend DEVE validar a propriedade do endereço antes de alterar o endereço padrão. O catálogo DEVE converter preços para centavos com aritmética decimal exata e rejeitar valores negativos, acima de R$ 1.000.000.000,00 ou com mais de duas casas decimais.

#### Cenário: edição de endereço não autorizado
- **Dado** um endereço padrão válido da conta
- **Quando** a conta enviar uma edição para um endereço inexistente ou de outra pessoa
- **Então** a operação falha e o endereço padrão atual permanece intacto

#### Cenário: preço com precisão inválida
- **Dado** um preço de produto negativo ou com mais de duas casas decimais
- **Quando** uma conta administradora tentar cadastrar ou atualizar o produto
- **Então** o backend rejeita o valor antes de salvar o produto

