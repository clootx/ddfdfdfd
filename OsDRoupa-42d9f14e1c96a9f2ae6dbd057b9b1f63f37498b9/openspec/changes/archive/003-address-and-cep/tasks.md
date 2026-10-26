# Tarefas — 003-address-and-cep

## Status: SCRIPTS PUBLICADOS; TESTES DE CONTA PENDENTES

### OpenSpec
- [x] Atualizar proposta, design e cenários de aceitação.
- [x] Consolidar os requisitos em `openspec/specs/addresses/spec.md`.
- [x] Registrar a change como ativa no índice.

### Implementação
- [x] Implementar `AddressState`, formulário, listagem, edição e CEP automático.
- [x] Enviar Bearer em leitura e mutações; retirar JWT da query string.
- [x] Tornar wrappers e CRUD direto de ENDERECO autenticados, com cliente derivado da sessão e verificação de propriedade.
- [x] Permitir múltiplos endereços removendo o índice único por tipo.

### Verificação
- [x] Validar sintaxe Xano das fontes locais desta change.
- [x] Publicar schemas e endpoints no workspace Xano, branch live `v1` (workspace `147975`).
- [ ] Exercitar CEP, múltiplos endereços, endereço padrão e isolamento entre duas contas.
- [ ] Confirmar o fluxo ponta a ponta com uma conta Xano de teste.
