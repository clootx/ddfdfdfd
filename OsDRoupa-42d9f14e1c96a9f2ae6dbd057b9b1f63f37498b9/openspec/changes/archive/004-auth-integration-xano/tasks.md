# Tasks — Change 004: Integração de Autenticação com Xano

## Status: CONCLUÍDO

## Checklist de Implementação

### Artefatos OpenSpec
- [x] `proposal.md` criado e atualizado com canonicals
- [x] `specs/auth-integration.md` criado e atualizado
- [x] `design.md` criado e atualizado
- [x] `tasks.md` criado e validado

### Código

- [x] **T1** — Adicionar `import httpx` no topo de `OSDroupa.py`
- [x] **T2** — Adicionar constantes `XANO_BASE`, `XANO_AUTH`, `XANO_PDB`, `XANO_TIMEOUT`
- [x] **T3** — Adicionar `auth_token: str = ""` e `current_user: dict = {}` ao `AuthState`
- [x] **T4** — Converter `handle_login` para `async def` com chamada real ao Xano e busca de perfil via `/auth/me`
- [x] **T5** — Converter `handle_register` para `async def` com chamada real ao Xano (`cadastraCliente`) e tratamento de CPF
- [x] **T6** — Adicionar tratamento de erro de rede em ambos os handlers
- [x] **T7** — Adicionar método `logout` e `check_auth_on_load` ao `AuthState`
- [x] **T8** — Criar `dashboard_page()` com guard de autenticação e identidade visual têxtil
- [x] **T9** — Registrar rota `/dashboard` no `app.add_page` com `on_load=AuthState.check_auth_on_load`
- [x] **T10** — Atualizar `openspec/changes/README.md` com a Change 004

### Verificação
- [x] Login com credenciais válidas → redireciona para `/dashboard` (validado via teste de integração)
- [x] Login com credenciais inválidas → erro "Invalid Credentials." exibido inline (validado via teste)
- [x] Cadastro com e-mail duplicado → erro exibido inline (validado via teste)
- [x] Cadastro bem-sucedido → usuário e cliente criados no Xano, redireciona para `/dashboard` (validado via teste)
- [x] Acesso a `/dashboard` sem token → guard de rota redireciona para `/` (validado)
- [x] Logout → limpa token, reseta estado e redireciona para `/` (validado)
