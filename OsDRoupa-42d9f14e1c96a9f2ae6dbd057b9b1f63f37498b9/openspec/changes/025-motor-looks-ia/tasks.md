# Tarefas — 025-motor-looks-ia

## Status: IMPLEMENTADA; TESTE COM CHAVE REAL E NAVEGADOR PENDENTES

### OpenSpec
- [x] Registrar proposta, requisitos, design e tarefas.
- [x] Registrar a change no índice `openspec/changes/README.md`.
- [x] Atualizar o design: structured outputs em vez de `tool_choice` forçado (erro 400 nos modelos atuais), modelo padrão `claude-opus-5-5`, `fallbacks: "default"` e timeout de 90 s.

### Configuração
- [x] Adicionar `anthropic==2.3.0` ao `requirements.txt`. Instalação validada em venv limpo junto com Reflex 0.9.12.
- [x] Adicionar `ANTHROPIC_API_KEY`, `OSDROUPA_AI_MODEL` e `OSDROUPA_AI_LOOKS_PER_HOUR` ao `.env.example`, sem valores reais.

### Serviço (Python)
- [x] Criar `OSDroupa/ai/stylist.py` com `build_prompt_context`, `LOOKS_SCHEMA`, `SYSTEM_PROMPT` e `request_looks`.
- [x] Implementar `validate_looks` (referências, disponibilidade, cobertura, rebaixamento). Validado com testes: referência inventada, peça suja, produto sem estoque e falta de cobertura.
- [x] Implementar a nova tentativa única, o tratamento de recusa e de erros por classe, o fallback e o limite por conta. Validado com cliente simulado: sem chave, JSON inválido seguido de válido, recusa, JSON inválido duas vezes, timeout e limite excedido.

### Estado (Reflex)
- [x] Adicionar `ai_proposals`, `ai_note`, `ai_loading`, `ai_notice`, `ai_error`, `generate_ai_looks` (`@rx.event(background=True)`) e `save_ai_proposal` em `WardrobeLifeState`.
- [x] Carregar o catálogo via `StoreState` e o estilo do perfil para o contexto.

### Interface
- [x] Criar a seção "Estilista com IA" em `/look-do-dia`: campo de observação, cards de proposta, selos de origem, link para a loja nas sugestões de compra e estados de carregamento, erro, limite e fallback.
- [x] Atualizar a política de privacidade para citar os dados enviados à IA (cidade/UF, ocasião, estilo, observação e atributos das peças).

### Verificação
- [x] Compilar o Reflex sem erros (`reflex compile`).
- [x] Confirmar que a chave, o prompt de sistema e o header beta não aparecem no build `.web`.
- [ ] Executar uma chamada real com `ANTHROPIC_API_KEY` (nenhuma chave disponível no ambiente de desenvolvimento usado).
- [ ] Executar os cenários 1–8 da spec no navegador.
- [ ] Confirmar que não houve regressão em `/looks` e `/calendario`.

### Pendências conhecidas
- [ ] O limite por conta fica na memória do processo; um deploy com várias instâncias precisa de contador compartilhado.
