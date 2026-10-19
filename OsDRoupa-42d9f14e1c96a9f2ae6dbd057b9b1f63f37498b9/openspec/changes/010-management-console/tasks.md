# Tarefas — 010-management-console

## Status: CHANGE INICIADA

### OpenSpec
- [x] Criar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.

### Backend Xano
- [x] Restringir fontes CRUD legadas de produto, cliente, pedido, item, transação e escrita de status a usuários `admin` no servidor.
- [ ] Criar endpoints com verificação de papel `admin` no servidor.
- [ ] Validar leitura, paginação, transições de status e acesso negado para `member`.
- [ ] Publicar depois de revisão no workspace.

### Frontend Reflex
- [x] Criar dashboard e páginas de catálogo, pedidos, clientes e relatórios.
- [x] Integrar estados 401/403, pendente e falha de rede.

### Verificação
- [x] Compilar, gerar build e validar HTTP 200 nas rotas de gestão.
- [x] Auditar as 76 rotas mutáveis genéricas locais: todas exigem `auth=user` e papel `admin`.
- [x] Validar sintaxe Xano dos endpoints CRUD protegidos localmente.
- [ ] Exercitar conta admin e member com Xano.
