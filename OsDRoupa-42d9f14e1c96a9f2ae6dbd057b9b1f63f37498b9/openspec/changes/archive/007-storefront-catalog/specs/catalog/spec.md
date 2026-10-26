# Especificação — Loja e Catálogo

## RF-CAT-01: Catálogo Xano

A página `/loja` deve buscar produtos pelo endpoint público `GET /api:EzKvuCov/produto`, apresentar nome, descrição, categoria, preço, disponibilidade e imagem, e exibir estados de carregamento, erro e catálogo vazio. O schema `PRODUTO` inclui `Categoria`.

### Cenário: catálogo carregado
- **Dado** que o endpoint retorna produtos
- **Quando** a pessoa abre a loja
- **Então** somente produtos classificados como roupas, calçados ou acessórios são apresentados com seus dados comerciais

### Cenário: catálogo contém registros sem categoria de moda
- **Dado** que o endpoint retorna registros sem categoria ou de categorias fora de moda
- **Quando** a loja termina de carregar
- **Então** esses registros não são mostrados como produtos de vestuário
- **E** a loja informa que o catálogo precisa ser preparado quando nenhum produto válido restar

### Cenário: falha ou lista vazia
- **Dado** que o Xano falha ou retorna uma lista vazia
- **Quando** a loja termina de carregar
- **Então** a pessoa vê uma mensagem adequada e pode tentar carregar novamente quando houver falha

## RF-CAT-02: Descoberta de produtos

A loja deve filtrar por categoria de moda, texto de nome ou descrição, disponibilidade e ordem de preço.

### Cenário: busca e filtros
- **Dado** que há produtos carregados
- **Quando** a pessoa pesquisa ou altera disponibilidade e ordenação
- **Então** a lista mostra somente os produtos correspondentes

As categorias de apresentação são Roupas, Calçados e Acessórios. A normalização aceita nomes detalhados dentro desses grupos e descarta categorias sem correspondência.

## RF-CAT-03: Detalhe do produto

A rota `/produto?id={product_id}` deve carregar o registro de `GET /api:EzKvuCov/produto/{product_id}` e permitir retornar à loja ou adicionar o item à sacola.

## RF-CAT-04: Sacola persistente

A pessoa deve poder adicionar produtos, alterar quantidades e remover linhas. A sacola persiste em `localStorage` e mostra quantidade e total.

### Cenário: sacola sobrevive à navegação
- **Dado** que um produto foi adicionado à sacola
- **Quando** a pessoa abre outra rota ou recarrega a aplicação
- **Então** a sacola continua disponível no mesmo navegador

Linhas antigas da sacola são preservadas para revisão, mas linhas sem categoria de moda válida bloqueiam o checkout e podem ser removidas pela pessoa.

## RF-CAT-05: Limite comercial

Esta change não cria pedidos nem processa pagamentos. Preços, quantidade e disponibilidade mantidos no navegador não são autoridade para concluir uma compra; o checkout posterior deve revalidá-los no backend.
