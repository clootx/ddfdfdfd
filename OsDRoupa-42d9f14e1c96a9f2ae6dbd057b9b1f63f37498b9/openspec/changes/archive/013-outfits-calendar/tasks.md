# Tarefas — 013-outfits-calendar

## Status: IMPLEMENTAÇÃO PUBLICADA; TESTES DE DUAS CONTAS E NAVEGADOR PENDENTES

### OpenSpec
- [x] Registrar proposta, requisitos e contratos.
- [x] Registrar a change no índice.

### Backend local
- [x] Criar e publicar o schema e os endpoints Xano para looks com validação de propriedade das peças, branch live `v1` (workspace `147975`).
- [ ] Testar os contratos com duas contas no workspace Xano.

### Frontend Reflex
- [x] Criar estado de looks associado ao usuário e migração idempotente.
- [x] Criar páginas responsivas `/looks` e `/calendario` e navegação integrada.
- [x] Preservar cache e informar indisponibilidade de sincronização.

### Verificação
- [x] Compilar a aplicação Reflex e validar a sintaxe Xano dos rascunhos locais.
- [ ] Validar navegação, criação, remoção e estados vazios no navegador.
- [ ] Exercitar propriedade das peças, duplicidade, migração e isolamento entre duas contas no Xano.
