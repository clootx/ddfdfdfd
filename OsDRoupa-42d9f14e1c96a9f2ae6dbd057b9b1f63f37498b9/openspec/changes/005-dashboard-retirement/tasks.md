# Tarefas — 005-dashboard-retirement

## Status: IMPLEMENTADA; validação de integração Xano pendente

### OpenSpec
- [x] Criar proposta, design, requisitos e cenários de aceitação para remover o dashboard.
- [x] Atualizar o contrato canônico de autenticação para o destino pós-login e pós-cadastro.

### Implementação
- [x] Login e cadastro com sessão validada retornam para `/#como-funciona`.
- [x] Remover a página `/dashboard` e seus helpers exclusivos.
- [x] Remover links para `/dashboard`; a navegação autenticada usa perfil, armário e endereços.

### Verificação
- [x] Conferir no código o destino dos dois fluxos de autenticação e a existência da âncora `#como-funciona`.
- [x] Confirmar que `/dashboard` responde 404 e que a aplicação compila.
- [ ] Validar login e cadastro bem-sucedidos contra uma conta Xano de teste e observar o destino no navegador.