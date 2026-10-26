# Especificação — catálogo de boutiques demonstrativas

## Requisitos

### RF-01 — Boutiques fictícias

A loja deve apresentar quatro vitrines claramente identificadas como fictícias: Ateliê Entrelinhas, Rua Viva Studio, Maré de Dentro e Forma Livre.

**Cenário: selecionar uma boutique**

- Dado que a pessoa está na página `/loja`
- Quando seleciona uma boutique
- Então a grade mostra somente os produtos dessa marca e coleção
- E a seleção pode ser combinada com categoria, disponibilidade e favoritos.

### RF-02 — Amplitude de catálogo

O catálogo demonstrativo deve cobrir tops e camisas, calças e denim, saias e bermudas, vestidos e conjuntos, casacos e jaquetas, peças esportivas, moda resort, calçados e acessórios.

**Cenário: explorar um catálogo por tipo de peça**

- Dado que produtos demonstrativos estão carregados
- Quando a pessoa busca por um nome, marca, coleção, tipo, cor ou material
- Então a loja apresenta os produtos correspondentes sem sair da vitrine.

### RF-03 — Ficha descritiva

Cada produto novo deve ter uma descrição editorial própria e informar marca, coleção, tipo, categoria, tamanhos, cores, material e caimento. A ficha deve funcionar mesmo quando um produto antigo ou remoto não possuir esses campos.

**Cenário: abrir um detalhe demonstrativo**

- Dado que a pessoa selecionou uma peça do catálogo
- Quando abre `/produto?id={id}`
- Então encontra descrição, grade de tamanhos, cores, material e caimento
- E a peça permanece identificada como demonstrativa.

### RF-04 — Catálogo persistido no Xano

O catálogo da apresentação deve ser lido da tabela Xano `PRODUTO`. Seus campos de boutique e ficha técnica são opcionais para preservar compatibilidade com produtos antigos. O endpoint de gestão deve validar autenticação e papel administrativo no backend.

**Cenário: carregar produtos demonstrativos**

- Dado que os registros demonstrativos foram aplicados à tabela `PRODUTO` do workspace Xano
- Quando a pessoa abre `/loja`
- Então a grade é carregada por `GET /produto`
- E a ficha de produto é carregada por `GET /produto/{produto_id}`.

**Cenário: cadastrar produto pela gestão**

- Dado que a pessoa autenticada possui papel `admin`
- Quando envia o formulário de produto
- Então o Xano valida a permissão e grava os campos enviados
- E uma conta sem papel administrativo recebe acesso negado.

### RF-05 — Sem cobrança demonstrativa

Todos os produtos adicionados para as vitrines são de demonstração. A sacola e o checkout não podem indicar pagamento recebido nem cobrar esses itens.

**Cenário: iniciar um pedido com peças de boutique fictícia**

- Dado que a sacola contém apenas itens demonstrativos
- Quando a pessoa prossegue para confirmar interesse
- Então o fluxo informa que a disponibilidade será confirmada pela loja
- E nenhum pagamento é cobrado.

### RF-06 — Responsividade

As vitrines, filtros, cartões e fichas de produto devem se adaptar a celular, tablet e desktop sem exigir rolagem horizontal.
