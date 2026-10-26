# Tarefas — 006-persistent-account-profile-wardrobe

## Status: IMPLEMENTAÇÃO PUBLICADA; TESTES COM CONTA REAL PENDENTES

### OpenSpec
- [x] Criar proposta, requisitos, cenários de aceitação e design técnico.
- [x] Registrar a change no índice e atualizar o contrato canônico de autenticação.

### Implementação
- [x] Persistir o JWT em cookie e validar `/auth/me` ao carregar páginas.
- [x] Usar Bearer em `GET /buscaCliente`; nunca enviar JWT em query string para carregar o perfil.
- [x] Criar rascunho Xano de `buscaCliente` autenticado, que deriva o cliente de `$auth.id`.
- [x] Criar página autenticada de perfil e navegação para perfil, armário e endereços.
- [x] Manter armário local separado por usuário; a sincronização Xano ficou definida na change 009.
- [x] Não gerar CPF a partir do celular ou horário no cadastro.
- [x] Restaurar a sessão também na rota pública de detalhe de artigo `/artigo`.

### Verificação
- [x] Validar compilação, build de produção, rotas HTTP e handshake Socket.IO.
- [x] Validar sintaxe Xano da fonte local `buscaCliente`.
- [ ] Confirmar login, cookie, recarregamento e bloqueio de rotas com uma conta Xano de teste.
- [ ] Confirmar comportamento sem sessão, com JWT inválido e com indisponibilidade do Xano.
- [x] Publicar `buscaCliente` no workspace Xano, branch live `v1` (workspace `147975`).
- [ ] Validar cadastro e perfil com dados reais no workspace Xano.
