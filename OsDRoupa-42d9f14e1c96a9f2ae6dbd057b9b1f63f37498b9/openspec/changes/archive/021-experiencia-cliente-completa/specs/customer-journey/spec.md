# Requisitos — experiência completa do cliente

## RF-01 — Perfil editável

O sistema DEVE permitir que a pessoa autenticada atualize nome, celular e preferências opcionais de estilo e tamanho, persistindo os dados no próprio perfil e sem permitir alteração do e-mail neste formulário.

### Cenário: salvar preferências

Dado que a pessoa autenticada informou dados válidos de perfil  
Quando salvar as alterações  
Então o sistema persiste os campos na conta autenticada e mostra confirmação.

### Cenário: data inválida

Dado que foi informada uma data de nascimento inválida ou futura  
Quando tentar salvar  
Então o sistema apresenta a validação e não altera o perfil.

## RF-02 — Desafios organizados

O sistema DEVE categorizar desafios, filtrar por categoria e situação, mostrar pontos e duração e oferecer um caminho para a atividade relacionada.

### Cenário: filtrar desafios

Dado que a pessoa abriu a lista de desafios  
Quando selecionar uma categoria ou estado  
Então somente os desafios correspondentes aparecem e o progresso total permanece visível.

## RF-03 — Fidelidade explicável

O sistema DEVE apresentar pontos, nível atual, avanço para o próximo nível e histórico de créditos derivados de desafios válidos. Os pontos NÃO DEVEM ser descritos como dinheiro, desconto ou saldo resgatável.

### Cenário: acompanhar nível

Dado que existem desafios concluídos na conta  
Quando abrir fidelidade  
Então o sistema mostra o nível, distância até o próximo marco e histórico de pontos.

## RF-04 — Favoritos separados por conta

O sistema DEVE permitir favoritar produtos, filtrar o catálogo por favoritos e manter cada lista separada por identificador de conta no navegador.

### Cenário: alternar conta

Dado que duas contas usam o mesmo navegador  
Quando uma pessoa favorita produtos  
Então esses favoritos só aparecem na lista da conta correspondente.

## RF-05 — Revisão de checkout

O checkout DEVE exibir itens e subtotal estimado, informar que preço, estoque e total são validados no servidor e comunicar a diferença entre demonstração e pagamento hospedado.

### Cenário: checkout demonstrativo

Dado que a sacola contém apenas produtos demonstrativos  
Quando enviar o pedido  
Então o sistema cria um pedido sem cobrança e informa que disponibilidade e condições aguardam confirmação da loja.

### Cenário: pagamento Mercado Pago

Dado que o backend de pagamento está configurado e a sacola contém produtos reais  
Quando iniciar o checkout  
Então a pessoa segue para o link HTTPS do Mercado Pago e o pedido permanece pendente até a confirmação do webhook validado.
