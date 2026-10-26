# Modelo de domínio

## Domínio principal

O sistema possui um domínio central de negócio relacionado a clientes, pedidos, produtos e status. O modelo atual sugere uma operação orientada a contexto comercial e operacional, com extensões para IA, localização e hardware.

## Entidades principais

### User
Representa o usuário autenticado do sistema.

Atributos esperados:
- id
- name
- email
- password
- account_id
- role
- created_at

Relacionamentos:
- pertence a uma conta
- pode estar vinculado a um cliente

### Account
Representa uma organização ou contexto de negócio.

Atributos esperados:
- id
- name
- description
- location
- created_at

### Cliente
Representa a pessoa ou entidade do cliente do negócio.

Atributos esperados:
- id
- nome
- celular
- cpf
- status_cliente_id
- user_id
- created_at

Relacionamentos:
- possui endereços
- realiza pedidos
- pode ter status associada

### Endereço
Representa um endereço do cliente.

Atributos esperados:
- id
- cliente_id
- tipoendereco_id
- logradouro
- numero
- complemento
- bairro
- referencia
- cep_id
- padrao

### CEP
Representa o código postal integrado ao endereço.

Atributos esperados:
- id
- cep
- uf
- cidade

### Produto
Representa o item comercial ou de estoque.

Atributos esperados:
- id
- Nome
- Descricao
- Qtd_Disp
- Url_Imagem
- Preco
- Precisa_Produzir
- created_at

### Pedido
Representa a transação principal do negócio.

Atributos esperados:
- id
- cliente_id
- Total
- Nfc_E
- Cod_Entrega
- status_pedido_id
- created_at

Relacionamentos:
- contém itens
- pode gerar OE/OP
- pode gerar cobrança
- pode gerar solicitação de cancelamento

### Item
Representa cada linha do pedido.

Atributos esperados:
- id
- pedido_id
- produto_id
- Qtd
- Valor_Unit
- Subtotal
- status_item_id
- created_at

### StatusPedido
Representa o estado do pedido.

### StatusItem
Representa o estado do item.

### Solicitação de cancelamento
Representa a pendência ou descrição de cancelamento.

Atributos esperados:
- id
- pedido_id
- motivo
- status_solcancelamento_id

### OE / OP
Representam operações ou ordens de execução associadas ao pedido.

Atributos esperados:
- id
- pedido_id
- status_oe_id / status_op_id
- created_at

### Transação
Representa evento financeiro ou de pagamento.

Atributos esperados:
- id
- clienteassas
- idpayment
- tipo
- valor
- datavenc
- descricao
- status_transacao_id

## Extensão de domínio para IA e smart wardrobe

Além do núcleo comercial, os anexos do projeto apontam para uma extensão do domínio para:
- peça de roupa
- status da peça (em armário, em uso, suja, lavando)
- RFID
- localização física do compartimento
- look / outfit
- recomendação de estilo
- métricas de uso e sustentabilidade

### Entidades futuras esperadas
- Clothes
- Outfits
- UsageLogs
- Locations
- StylePreferences

## Regras de negócio esperadas

1. Usuário autenticado deve ter contexto de conta e perfil.
2. Cliente deve estar vinculado a um usuário ou ao menos à conta de origem.
3. Pedido deve refletir um cliente válido e itens consistentes.
4. Item deve respeitar produto e quantidade válida.
5. Status deve ser rastreável e válido para o ciclo do pedido.
6. Transação deve estar associada ao cliente e ao processo de cobrança.
7. IA e hardware não podem existir sem o modelo base de peça, status e localização.

## Observação importante

O modelo atual já capta a base de negócio. O que precisa ser resolvido é a unificação entre o modelo transacional atual e a visão de produto mais avançada, especialmente no que tange a peça/armário/uso/IA.

## Extensões locais — Change 020

- **GarmentWearEvent:** registra a peça usada, a ocasião e a data; pertence à conta e permite calcular custo por uso somente se houver preço de compra informado.
- **PackingPlan:** agrupa destino, datas, ocasião e IDs de peças do armário do próprio usuário.
- **TailoringRequest:** registra serviço, peça, observações, data preferida e etapa de atendimento; a gestão pode atualizar o estado.
- **ChallengeCompletion:** chave única por conta e desafio. A pontuação vem de uma lista autorizada no servidor, não de um saldo enviado pelo navegador.
- **Testimonial:** relato ligado à conta, com consentimento, opção anônima e estado de moderação; só relatos aprovados ficam públicos.
- **PrivacyRequest:** solicitação privada associada à conta, com tipo, detalhes e etapa de análise.
- **PaymentOrder:** pedido com gateway e ID da Order, URL de checkout, referência/idempotência e estado. O evento de webhook é deduplicado; o retorno do navegador não marca pagamento como confirmado.

Estas entidades estão implementadas no SQLite local. Os contratos correspondentes ainda precisam ser portados e publicados no Xano para uso remoto.
