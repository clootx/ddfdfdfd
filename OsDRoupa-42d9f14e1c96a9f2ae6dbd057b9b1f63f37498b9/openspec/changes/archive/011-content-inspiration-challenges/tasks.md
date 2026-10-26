# Tarefas — 011-content-inspiration-challenges

## Status: IMPLEMENTAÇÃO PUBLICADA; TESTES DE ISOLAMENTO PENDENTES

### OpenSpec
- [x] Registrar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.

### Frontend Reflex
- [x] Criar inspiração, lista de artigos, detalhe e desafios.
- [x] Validar sessão em desafios e separar progresso por conta.
- [x] Validar novamente a sessão antes de gravar conclusão de desafio.
- [x] Manter progresso local particionado por conta para uso sem conexão.
- [x] Ler e gravar conclusões em endpoints autenticados do Xano, com fallback local.
- [x] Exibir se o progresso está sincronizado ou apenas no navegador.
- [x] Mostrar progresso pessoal de forma visual e aplicar microinterações com movimento reduzido.

### Verificação
- [x] Compilar, gerar build e validar HTTP 200 em inspiração, artigos, detalhe e desafios.
- [x] Validar sintaxe Xano das fontes locais da tabela e endpoints de desafio.
- [x] Publicar tabela e endpoints de desafios no workspace Xano, branch live `v1` (workspace `147975`); prévia em 2026-10-22 confirmou que não há diferenças pendentes.
- [ ] Exercitar isolamento entre duas contas no workspace Xano.
- [ ] Exercitar rota privada e slug inválido no navegador.
