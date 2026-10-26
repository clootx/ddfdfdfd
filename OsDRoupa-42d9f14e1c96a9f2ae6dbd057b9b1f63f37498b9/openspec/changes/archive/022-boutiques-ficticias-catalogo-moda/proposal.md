# Proposta — 022-boutiques-ficticias-catalogo-moda

## Contexto

A loja tinha uma vitrine pequena e sem identidade própria para os produtos. A apresentação precisa parecer um marketplace de demonstração completo, com coleções fictícias, tipos variados de roupa e informações suficientes para comparar peças.

## Objetivo

Ampliar `/loja` e `/produto` com quatro boutiques fictícias, um catálogo abrangente de roupas, calçados e acessórios, filtros por marca e coleção, e descrições demonstrativas com tamanho, cor, material e caimento.

## Escopo

- Criar vitrines para Ateliê Entrelinhas, Rua Viva Studio, Maré de Dentro e Forma Livre.
- Incluir alfaiataria, denim, streetwear, resort, vestidos, saias, tops, peças esportivas, calçados e acessórios.
- Guardar os novos atributos e os 29 produtos demonstrativos na tabela `PRODUTO` do Xano.
- Disponibilizar leitura pública do catálogo e criação administrativa autenticada no Xano.
- Manter o catálogo SQLite como alternativa local de desenvolvimento, sem torná-lo fonte de verdade da apresentação.
- Exibir os atributos no cartão, no detalhe e no formulário administrativo.
- Manter todos os novos itens sinalizados como demonstrativos e sem cobrança.

## Fora de escopo

- Lojas, marcas, estoque, composição têxtil ou imagens de produtos reais.
- Ativação de pagamento, validação de disponibilidade comercial ou afirmações de certificação de materiais.
- Alterar ou apagar produtos que já existam no banco.

## Critérios de aceite

- A loja diferencia as quatro boutiques e permite filtrar por boutique e coleção.
- A busca encontra nome, descrição, marca, coleção, tipo de peça, cor e material.
- Cada produto demonstrativo apresenta descrição, categoria, tipo, marca, coleção, tamanhos, cores, material e caimento.
- Produtos antigos sem metadados continuam abrindo com valores de apresentação padrão.
- O formulário administrativo cria produtos pelo Xano com autorização validada no backend.
- A navegação e os cartões permanecem utilizáveis em telas estreitas.
