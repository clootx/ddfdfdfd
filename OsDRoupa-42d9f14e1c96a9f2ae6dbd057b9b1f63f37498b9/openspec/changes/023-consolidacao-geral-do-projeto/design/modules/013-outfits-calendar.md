# Design — 013-outfits-calendar

## Dados e propriedade

`LOOK_CLIENTE` contém cliente, chave local única, nome, ocasião, data planejada e as chaves locais das peças escolhidas. O endpoint de criação deriva o cliente de `$auth.id` e confirma que todas as chaves enviadas pertencem ao mesmo cliente antes de persistir o look.

## Contratos Xano locais

| Método e rota | Acesso | Comportamento |
|---|---|---|
| `GET /meusLooks` | `auth=user` | Retorna looks da conta autenticada |
| `POST /meusLooks` | `auth=user` | Cria ou devolve o look da mesma `chave_local`, validando a propriedade das peças |
| `DELETE /meusLooks/{look_id}` | `auth=user` | Remove somente look do cliente autenticado |

As fontes Xano desta change são locais. Precisam ser importadas e exercitadas no workspace antes de habilitar a sincronização em produção.

## Reflex

- `/looks` usa os componentes e tokens visuais do OSDROUPA, permite buscar e selecionar peças do armário e cadastrar ocasião/data.
- `/calendario` mostra looks planejados em ordem cronológica e liga de volta à montagem.
- Estado e cache são separados por usuário. A integração remota usa `chave_local` idempotente; falha mantém o cache e deixa claro quando um look ainda não foi sincronizado.
- A navegação do armário, loja e área da conta oferece acesso às duas páginas. O layout usa uma coluna em telas pequenas e duas colunas em telas médias.

## Segurança e falhas

- O frontend envia chaves de peça, mas o Xano valida propriedade em cada criação. Nenhum ID de cliente vem do navegador.
- A leitura e remoção são filtradas pelo cliente derivado do token.
- `401/403` encerra a sessão local; falhas transitórias preservam rascunhos e identificadores para uma migração repetível.
