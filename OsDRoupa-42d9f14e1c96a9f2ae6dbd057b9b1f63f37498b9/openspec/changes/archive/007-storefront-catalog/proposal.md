# Proposta — 007-storefront-catalog

## Contexto

O backend expõe o catálogo `PRODUTO` no grupo Xano `DB_BRUNO_MAGNO`. A primeira versão da loja exibe qualquer registro desse endpoint, sem distinguir vestuário de outros itens. A leitura atual do catálogo remoto encontrou 15 registros de alimentos e bebidas, sem categoria; esses dados não podem ser apresentados como roupas nem levados ao checkout do OSDROUPA.

## Objetivo

Criar uma área de loja de moda ligada ao catálogo Xano, com categorias de vestuário, busca, detalhe e sacola persistida no navegador. A interface deve ocultar registros sem categoria reconhecida como roupa, calçado ou acessório e explicar quando os dados do Xano ainda não estiverem preparados.

## Escopo incluído

- Adicionar o campo `Categoria` à tabela `PRODUTO` e criar `/loja`, com categorias Roupas, Calçados e Acessórios, busca por nome e descrição, filtro de disponibilidade, ordenação por preço e estados de carregamento, erro, catálogo vazio e configuração pendente.
- Criar `/produto?id={product_id}`, carregando o produto diretamente pelo endpoint do Xano.
- Apresentar somente produtos cuja categoria possa ser reconhecida como vestuário, calçado ou acessório.
- Criar `/carrinho`, permitindo adicionar, remover e alterar quantidades, com subtotal e total calculados na interface.
- Persistir a sacola no `localStorage` e manter navegação entre loja, produto, sacola e áreas autenticadas.
- Atualizar as especificações canônicas do catálogo.

## Fora do escopo

- Criar pedido ou item no Xano, reservar estoque ou iniciar pagamento; isso será tratado na próxima change de pedidos e pagamentos.
- Criar variantes, frete, cupons ou avaliação de produtos.
- Tratar valores guardados no navegador como fonte confiável para preço ou estoque. O checkout deve validá-los novamente no backend.

## Dependências e impactos

- **Modelagem de dados:** tabela `PRODUTO` (`Nome`, `Descricao`, `Categoria`, `Qtd_Disp`, `Url_Imagem`, `Preco`, `Precisa_Produzir`).
- **APIs:** leitura pública `GET /api:EzKvuCov/produto` e `GET /api:EzKvuCov/produto/{produto_id}`.
- **Frontend:** novos estados e páginas Reflex para loja, produto e carrinho.
- **Integrações externas:** nenhuma além do Xano já configurado.

## Dependência de dados

A alteração do schema e a classificação/substituição dos registros atuais precisam ser importadas no workspace Xano. Até isso ocorrer, a loja deve informar que o catálogo de moda ainda está sendo preparado; a existência de resposta HTTP 200 não significa que haja produtos de vestuário válidos.
