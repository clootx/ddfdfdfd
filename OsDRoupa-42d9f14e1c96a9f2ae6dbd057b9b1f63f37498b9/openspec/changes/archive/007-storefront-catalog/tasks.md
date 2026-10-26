# Tarefas — 007-storefront-catalog

## Status: INTERFACE E SCHEMA PUBLICADOS; CATÁLOGO DE MODA PENDENTE

### OpenSpec
- [x] Registrar proposta, design, requisitos e cenários.
- [x] Criar especificação canônica do catálogo.
- [x] Registrar a change no índice.
- [x] Criar design técnico da integração e contratos locais.

### Implementação
- [x] Criar estado e cliente para os endpoints públicos de produto.
- [x] Criar página de loja com busca, disponibilidade e ordenação.
- [x] Criar detalhe do produto em `/produto?id={product_id}`.
- [x] Criar carrinho persistente com edição de quantidade e remoção.
- [x] Integrar navegação da loja com conta, perfil e armário.
- [x] Adicionar categoria de moda ao schema local e filtros de Roupas, Calçados e Acessórios.
- [x] Ocultar registros sem categoria reconhecida e exibir mensagem de preparação do catálogo.

### Verificação
- [x] Compilar o app Reflex e gerar o build de produção.
- [x] Validar sintaxe Xano do schema local de produto com o validador oficial.
- [x] Confirmar HTTP 200 em `/loja`, `/produto?id=15` e `/carrinho`, e HTTP 404 em `/dashboard`.
- [x] Consultar o catálogo remoto em modo somente leitura: 15 registros atuais não têm categoria e são alimentos/bebidas, não vestuário.
- [x] Publicar o schema de produto atualizado no workspace Xano, branch live `v1` (workspace `147975`).
- [ ] Cadastrar produtos de moda no Xano e validar respostas com dados reais; o catálogo atual contém alimentos e bebidas.
- [ ] Validar visualmente os estados de catálogo vazio, mal classificado e indisponível no navegador.
- [ ] Validar que resposta vazia ou falha da API não cria pedidos ou cobranças.
