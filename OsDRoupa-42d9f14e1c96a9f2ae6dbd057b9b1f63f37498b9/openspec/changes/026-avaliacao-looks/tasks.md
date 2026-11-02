# Tarefas — 026-avaliacao-looks

## Status: IMPLEMENTADA; TESTE COM CHAVE REAL E NAVEGADOR PENDENTES

### OpenSpec
- [x] Registrar proposta, requisitos, design e tarefas.
- [x] Registrar a change no índice `openspec/changes/README.md`.

### Serviço (Python)
- [x] Adicionar `EVALUATION_SCHEMA`, `EVALUATION_PROMPT` e o campo `avaliacao` em `LOOKS_SCHEMA`.
- [x] Extrair `_structured_call` (compartilhada por geração e avaliação) e `_Inventory.piece` (resolução de referências).
- [x] Implementar `request_evaluation`, `validate_evaluation`, `closet_pieces` e `apply_swap`. Validado com testes: troca válida, entrada inexistente rebaixada, peça de saída fora do look tratada como acréscimo, limite de 3 trocas, nota fora da faixa, troca não aplicável recusada e cobertura recalculada.

### Estado (Reflex)
- [x] `WardrobeLifeState.apply_ai_swap`.
- [x] `LookState.evaluate_look` (background), `toggle_review_swap`, `save_adjusted_look` e `close_review`.

### Interface
- [x] Avaliação e "Como melhorar" (com botão Aplicar) nos cards da IA em `/look-do-dia`.
- [x] Botão "Avaliar com IA" nos cards de `/looks` e painel de avaliação com trocas selecionáveis e "Salvar versão ajustada".

### Verificação
- [x] Compilar o Reflex sem erros.
- [x] Executar os testes do serviço (geração da 025 e avaliação da 026) com cliente simulado.
- [ ] Executar uma chamada real com `ANTHROPIC_API_KEY`.
- [ ] Executar os cenários 1–6 da spec no navegador.
