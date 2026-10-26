# Design Técnico — 006-persistent-account-profile-wardrobe

## Sessão e validação

- `AuthState.auth_token` usa `rx.Cookie` com caminho `/`, SameSite Lax, flag Secure e duração de 86400 segundos.
- `_sync_session(token)` valida o JWT em `GET {XANO_AUTH}/me` com `Authorization: Bearer <token>`, atualiza `current_user` e consulta `GET {XANO_PDB}/buscaCliente` com o mesmo cabeçalho.
- O endpoint `buscaCliente` usa `auth=user` e deriva `CLIENTE.user_id` a partir de `$auth.id`. O navegador não envia o token em query string.
- Home, login e cadastro restauram sessão no `on_load`. Rotas privadas validam a sessão antes de consultar dados.
- Falhas de autenticação inválida limpam token e dados da conta; falhas transitórias de rede mantêm o cookie e mostram estado de erro.

## Cadastro

O formulário coleta nome, e-mail, celular e senha. CPF não é solicitado e não pode ser inventado a partir do celular ou de um valor temporal. O endpoint Xano aceita `cpf` opcional para fluxos que o coletarem explicitamente.

## Perfil

`/perfil` apresenta informações atuais recebidas de `/auth/me` e `buscaCliente`, com estado visual de conta validada. Não há mutação de dados cadastrais nesta change.

## Armário

`AuthState` mantém `wardrobe_items` no estado Reflex e persiste o mapa em `rx.LocalStorage`, indexado pelo ID de cada usuário. Ao carregar o armário, `WardrobeState` seleciona somente a lista daquele ID. A sincronização com Xano e entre dispositivos está especificada na change 009.

## Rotas

| Rota | Acesso | Validação / carregamento |
|---|---|---|
| `/` | Pública | `AuthState.restore_session` |
| `/login`, `/cadastro` | Públicas | `AuthState.restore_session` |
| `/perfil` | Privada | `AuthState.require_authenticated` |
| `/armario` | Privada | `WardrobeState.load_wardrobe` |
| `/enderecos` | Privada | `AddressState.load_addresses` |

## Limite de validação

A fonte `buscaCliente` é um rascunho local. O contrato só estará ativo após importação no workspace Xano e validação com uma conta de teste.