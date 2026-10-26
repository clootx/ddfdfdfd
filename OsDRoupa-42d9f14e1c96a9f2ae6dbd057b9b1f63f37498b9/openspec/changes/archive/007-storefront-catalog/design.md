# Design — 007-storefront-catalog

## Decisões

- `PRODUTO.Categoria` separa a loja de moda de outros registros que possam existir no banco compartilhado.
- A interface agrupa categorias detalhadas em Roupas, Calçados ou Acessórios. Registros sem correspondência ficam fora da vitrine, do detalhe e da sacola.
- `StoreState` continua responsável pela leitura pública do catálogo e pelo estado local da sacola. Preço e estoque no navegador não têm autoridade para criar pedidos.
- A loja distingue catálogo vazio de catálogo carregado sem produtos de moda. O segundo estado explica que o schema e os dados do Xano precisam ser preparados.

## Contrato de dados

Cada produto da API pública `GET /api:EzKvuCov/produto` e `GET /api:EzKvuCov/produto/{id}` deve conter os campos existentes (`id`, `Nome`, `Descricao`, `Qtd_Disp`, `Url_Imagem`, `Preco`, `Precisa_Produzir`) e `Categoria`. `Categoria` é texto, com valores ou nomes detalhados que possam ser classificados em roupas, calçados ou acessórios.

O export local da tabela inclui o novo campo. As consultas de lista e detalhe leem a tabela e retornam esse campo após a migração do schema no Xano. O workspace remoto ainda precisa importar a alteração e preparar os registros; isso não é executado automaticamente pelo app.

## Fluxo

1. `/loja` busca a lista, normaliza categoria e descarta itens sem classificação de moda.
2. Busca textual, filtro de categoria, disponibilidade e ordenação são aplicados à lista válida.
3. `/produto?id={id}` valida a mesma classificação antes de expor o item.
4. A sacola restaura `localStorage` e atualiza dados das linhas presentes no catálogo válido. Linhas antigas não são apagadas silenciosamente; o checkout bloqueia itens sem categoria de moda e orienta a pessoa a removê-los.
5. O checkout posterior deve validar produto, cliente, endereço, preço e estoque no servidor; esta change não cria pedido nem cobrança.

## Migração e validação

Importar a tabela `PRODUTO` atualizada no Xano e atribuir categoria apenas a produtos de moda reais. Os 15 registros vistos no catálogo remoto durante a implementação eram alimentos/bebidas sem categoria; não devem receber categoria de moda artificialmente. Confirmar depois uma resposta vazia/sem moda, uma resposta com itens classificados e falha de API.
