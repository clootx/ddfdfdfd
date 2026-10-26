# Tarefas — 010-management-console

## Status: BASE DA CONSOLE PUBLICADA; TRANSIÇÕES E CONCILIAÇÃO PENDENTES

> O backend SQLite da Change 017 já implementa resumo reconciliado, paginação e transições permitidas de pedidos. As tarefas abertas abaixo tratam dos endpoints e da validação remota no Xano.

### OpenSpec
- [x] Criar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.

### Backend Xano
- [x] Restringir fontes CRUD legadas de produto, cliente, pedido, item, transação e escrita de status a usuários `admin` no servidor.
- [x] Criar endpoints locais de leitura para resumo, produtos, pedidos, clientes e histórico, todos com verificação `admin`.
- [x] Paginar as listas administrativas no Xano e na interface.
- [ ] Implementar agregação financeira reconciliada e transições permitidas de status de pedido.
- [ ] Validar leitura, paginação, transições de status e acesso negado para `member`.
- [x] Publicar a base da console depois de revisão no workspace, branch live `v1` (workspace `147975`).

### Frontend Reflex
- [x] Criar dashboard e páginas de catálogo, pedidos, clientes e relatórios.
- [x] Integrar estados 401/403, pendente e falha de rede.
- [x] Aplicar hierarquia visual responsiva e microinterações com suporte a movimento reduzido.

### Verificação
- [x] Compilar, gerar build e validar HTTP 200 nas rotas de gestão.
- [x] Auditar as 76 rotas mutáveis genéricas locais: todas exigem `auth=user` e papel `admin`.
- [x] Validar sintaxe Xano dos endpoints CRUD protegidos localmente.
- [x] Validar sintaxe dos novos endpoints de leitura e resposta paginada.
- [x] Marcar CPF do cliente como campo privado no schema Xano.
- [ ] Exercitar conta admin e member com Xano.
