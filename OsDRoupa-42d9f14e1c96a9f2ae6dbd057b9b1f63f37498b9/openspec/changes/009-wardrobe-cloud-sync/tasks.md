# Tarefas — 009-wardrobe-cloud-sync

## Status: IMPLEMENTAÇÃO INICIADA; VALIDAÇÃO XANO PENDENTE

### OpenSpec
- [x] Registrar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.

### Backend Xano local
- [x] Criar fonte local da tabela privada `ROUPA_CLIENTE` com chave idempotente.
- [x] Criar fontes locais para leitura, inclusão e remoção autenticadas com verificação do proprietário.
- [ ] Validar fontes e contratos no workspace Xano.

### Frontend Reflex
- [x] Ler e escrever peças no Xano com sessão validada.
- [x] Migrar cache local por conta sem duplicação.
- [x] Exibir estado sincronizado ou cache local sem conexão.

### Verificação
- [x] Compilar, gerar build de produção, validar HTTP 200 em `/armario` e handshake Engine.IO; confirmar `/dashboard` com 404.
- [x] Validar sintaxe Xano das fontes locais da change.
- [x] Verificar que o cache local permanece separado por conta e a chave `chave_local` mantém a migração repetível.
- [ ] Exercitar isolamento entre contas, migração repetida e falhas de conexão no workspace Xano.
