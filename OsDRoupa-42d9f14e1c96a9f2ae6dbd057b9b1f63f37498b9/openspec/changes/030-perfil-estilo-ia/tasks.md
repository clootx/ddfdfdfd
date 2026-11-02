# Tarefas — 030-perfil-estilo-ia

## Status: IMPLEMENTADA NO SQLITE (ETAPA 7); XANO EM RASCUNHO; NAVEGADOR PENDENTE

### SQLite e app
- [x] Tabela `look_feedback`, coluna `users.ai_personalization`, rotas `feedbackLooks` GET/POST/DELETE.
- [x] `personalizacao_ia` em `buscaCliente` e `perfil` (mantida quando omitida; rejeita não booleano).
- [x] `stylist.build_style_profile` e `perfil_estilo` no contexto; regras de personalização no prompt.
- [x] `generate_ai_looks` respeita o opt-out (sem estilo, sem perfil).
- [x] Card: 👍 / 👎 com motivos; ocultos com a personalização desligada ou na sugestão básica.
- [x] Perfil: interruptor e "Apagar meu histórico de avaliações".
- [x] Texto de privacidade.
- [x] Testes: feedback (ida e volta, chaves de outra conta, validação, separação por conta, apagar), opt-out no perfil, perfil de estilo (uso, feedback, peças sujas, sem dados pessoais). `pytest` 149 passed.

### Xano (depende do workspace)
- [x] Rascunhos: `xano/table/feedback_look.xs`, `feedback_looks_GET/POST/DELETE.xs`, campo `personalizacao_ia` em `cliente.xs` e `perfil_PATCH.xs`.
- [ ] Importar, validar e publicar. Conferir o filtro `in` e incluir o descarte de chaves que não são da conta no POST.

### Validação
- [ ] Testar no navegador: avaliar looks, desligar a personalização, apagar histórico.
