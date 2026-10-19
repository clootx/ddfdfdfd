# Especificação Consolidada — Loja e Catálogo

## RF-CAT-01: Catálogo Xano

A página `/loja` busca produtos pelo endpoint público `GET /api:EzKvuCov/produto` e mostra nome, descrição, categoria, preço, disponibilidade e imagem. O schema `PRODUTO` inclui `Categoria`; somente roupas, calçados e acessórios podem aparecer na vitrine. A página trata carregamento, erro, resposta vazia e tentativa de recarga.

## RF-CAT-02: Integridade de categoria

Registros sem categoria de moda reconhecida não são apresentados como produtos da loja. Se o endpoint retornar dados, mas nenhum produto tiver categoria válida, a interface informa que o catálogo de moda precisa ser preparado no Xano.

## RF-CAT-03: Descoberta

A loja permite filtrar pelas categorias Roupas, Calçados e Acessórios, pesquisar nome e descrição, filtrar disponibilidade e ordenar por preço.

## RF-CAT-04: Detalhe

A rota `/produto?id={product_id}` busca o produto por `GET /api:EzKvuCov/produto/{product_id}` e oferece retorno à loja e inclusão na sacola.

## RF-CAT-05: Sacola

A sacola permite adicionar, remover e alterar quantidades, mostra subtotal e total, e persiste no `localStorage` do navegador.

Linhas antigas são preservadas para a pessoa revisar. O checkout bloqueia linhas sem categoria de moda válida e orienta a remoção manual.

## RF-CAT-06: Autoridade do backend

Dados da sacola no navegador são apenas estado de interface. O checkout futuro deve confirmar preço, estoque, cliente e totais no backend antes de criar pedido ou cobrança.
