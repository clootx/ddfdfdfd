# Design — 010-management-console

## Autorização

`AuthState` valida a sessão em `/auth/me`. Cada endpoint de gestão consulta o usuário autenticado e exige `role == "admin"` no Xano. A checagem frontend serve para navegação e feedback; nunca substitui autorização no servidor.

## Endpoints previstos

| Método e rota | Saída / ação |
|---|---|
| `GET /adminResumo` | Indicadores agregados do dia e mês |
| `GET /adminProdutos` | Catálogo e disponibilidade |
| `GET /adminPedidos` | Fila operacional com estado atual |
| `PATCH /adminPedido/{id}` | Alteração permitida do estado operacional |
| `GET /adminClientes` | Busca paginada de clientes |
| `GET /adminRelatorios` | Séries agregadas, sem dados de pagamento sensíveis |

Todos exigem `auth=user` e checagem do papel no Xano. As listas retornam até 100 registros por página; a interface pede 20 e oferece navegação entre páginas. O resumo mostra contagens de pedidos, produtos e clientes. Vendas mensais ficam identificadas como pendentes até que os pagamentos tenham conciliação confiável. A lista de relatórios mostra histórico operacional por pedido, sem se apresentar como total financeiro agregado. Operações de escrita validarão transições de status e não aceitarão totais recalculados no browser.

As fontes genéricas antigas para produto, cliente, pedido, item, transação e escrita de status também exigem `role == "admin"`. Leitura de produto continua pública para a vitrine; perfil, endereços, pedidos e armário usam endpoints próprios com filtro de proprietário. A cobrança legada com valor livre e a criação de cliente baseada em `authtoken` ficam desativadas.

## Páginas

O Reflex compartilha navegação, cabeçalho e estados de carregamento/erro entre as páginas. Listas usam respostas paginadas normalizadas do grupo `DB_BRUNO_MAGNO`; quando a API não existe, a página informa que a integração está pendente. Respostas 401/403 não mostram dados e retornam ao acesso negado/login. Microinterações usam transições curtas e respeitam `prefers-reduced-motion`.

## Direção visual

Usar a energia de comunidade, progresso e desafios da SquadEasy junto da hierarquia editorial e foco em UX/UI da We Are OSM. Aplicar a paleta própria do OSDROUPA, tipografia legível, cartões com respiro e interações discretas. Referências servem como direção; não reutilizar logotipos, textos ou imagens dos sites.

## Integração

Fontes Xano locais não significam publicação remota. Os endpoints de leitura e escrita devem ser revisados com contas `admin` e `member` antes de liberar a console.
