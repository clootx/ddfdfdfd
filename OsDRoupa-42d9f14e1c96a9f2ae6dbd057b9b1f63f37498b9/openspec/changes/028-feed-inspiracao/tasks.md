# Tarefas — 028-feed-inspiracao

## Status: IMPLEMENTADA NO MODO SQLITE; XANO EM RASCUNHO; NAVEGADOR PENDENTE

### OpenSpec
- [x] Registrar proposta, requisitos, design e tarefas.
- [x] Registrar a change no índice `openspec/changes/README.md`.

### Backend local (SQLite)
- [x] Criar as tabelas `inspirations` e `inspiration_saves` com índices (criação idempotente na inicialização).
- [x] Implementar `_inspiration_routes` com os 9 contratos e a sanitização (`_clean_inspiration`, `_clean_image_ref`).
- [x] Testes ponta a ponta em banco temporário: idempotência, chave de outra conta, imagem e peças inválidas, foto do armário descartada, `javascript:` descartado, feed vazio para privado/pendente, consentimento, dono, salvar só publicado, salvar duas vezes, admin 403/200, anonimato do feed, filtros válidos e inválidos, remover salvo, exclusão por terceiro negada, exclusão pela dona e acesso sem sessão (401).

### Backend Xano (rascunhos)
- [x] `xano/table/look_inspiracao.xs` e `xano/table/inspiracao_salva.xs`.
- [x] 9 endpoints em `xano/api/panela_de_barro/` (`feed_inspiracoes_GET`, `minhas_inspiracoes_GET/POST`, `minhas_inspiracoes_id_DELETE`, `publicar_inspiracao_id_POST`, `inspiracoes_salvas_id_POST/DELETE`, `admin_inspiracoes_GET`, `admin_inspiracoes_id_PATCH`).
- [ ] Validar a sintaxe e importar no workspace Xano. Atenção a filtros não usados antes no projeto (`starts_with`, `json_encode`, `contains`, `map`) e à expressão de filtro opcional em `where`.
- [ ] Testar os contratos com contas `member` e `admin` no Xano.

### Frontend (Reflex)
- [x] `WardrobeLifeState.save_ai_inspiration` e botão "Guardar inspiração" nos cards da IA.
- [x] `InspirationState`, dataclasses `Inspiration`/`InspirationPiece`, abas, filtros, paginação, salvos, envio com consentimento e exclusão em `/inspiracao`, mantendo as ideias editoriais.
- [x] `/gestao/inspiracoes` com aprovação e recusa, mais item no menu de gestão.
- [x] Teste de integração: payload do card → backend local → `InspirationState._to_inspiration`, sem vazar foto do armário.
- [x] Compilar o Reflex sem erros; regressão das Changes 025 a 027.

### Verificação manual
- [ ] Executar os cenários 1–6 da spec no navegador (definir `OSDROUPA_ADMIN_EMAIL` antes de cadastrar a conta admin no modo SQLite).

### Pendências conhecidas
- [ ] Em produção com várias instâncias, usar volume compartilhado ou armazenamento de objetos para `uploaded_files/looks`.
