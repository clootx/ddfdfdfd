# Design — 022-boutiques-ficticias-catalogo-moda

## Dados e backend

O Xano é a fonte de verdade do catálogo no modo exigido para apresentação. Manter `Categoria` nos valores atuais de roupas, calçados e acessórios e adicionar os campos opcionais `Marca`, `Colecao`, `Tipo`, `Tamanhos`, `Cores`, `Material` e `Caimento` à tabela `PRODUTO`. O contrato JSON usa esses mesmos nomes; produtos antigos continuam funcionando com valores de apresentação padrão na camada Reflex.

`xano/table/produto.xs` contém os campos e os 29 produtos demonstrativos das quatro boutiques. O catálogo público usa `GET /produto` e `GET /produto/{produto_id}`. A central de gestão usa `GET /adminProdutos` e `POST /adminProdutos`; criação e edição ficam restritas a administradores no Xano. Todos os novos registros usam `demonstracao=true`; o checkout demonstrativo continua sem gateway e sem cobrança.

`professormateria/demo_catalog.py` e a inicialização SQLite continuam disponíveis para desenvolvimento local e fallback. A camada Reflex não é migrada para Xano: só os dados persistidos, as validações de negócio e os endpoints correspondentes são implementados no Xano. Aplicar os arquivos `.xs` ao workspace remoto é uma etapa separada e precisa ser verificada lá.

## Loja e navegação

`StoreState._normalize_product()` normaliza o contrato Xano e o formato local de desenvolvimento. Busca considera nome, descrição, marca, coleção, tipo, cor e material. Filtros combináveis cobrem categoria, boutique, coleção, disponibilidade e favoritos.

`/loja` apresenta cartões para as boutiques e conduz a seleção para o filtro correspondente. `/produto?id={id}` exibe uma ficha de detalhes com tamanhos, cores, material e caimento. Os cartões de catálogo destacam marca, coleção, tipo e selo demonstrativo. A grade usa uma coluna no celular, duas no tablet e três no desktop; as boutiques usam uma, duas e quatro colunas conforme a largura disponível.

## Administração

O formulário administrativo envia os novos campos ao endpoint Xano `POST /adminProdutos`. O endpoint exige autenticação e papel `admin`; os campos de descrição são texto simples e opcionais para preservar produtos existentes. O cadastro local SQLite permanece disponível apenas quando o modo local é escolhido.

## Direção editorial

As quatro identidades são inventadas para a apresentação do projeto. A seleção traduz referências amplas de 2026 — volumes utilitários e barrel, lenços como elemento de styling, conjuntos, bermudas, estampas retrô e alfaiataria mais marcada — em sugestões vestíveis. As descrições não alegam propriedades certificadas nem disponibilidade de venda real.
