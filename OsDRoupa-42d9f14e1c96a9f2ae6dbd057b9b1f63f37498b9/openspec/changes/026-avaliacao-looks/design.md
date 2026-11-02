# Design Técnico — 026-avaliacao-looks

## Visão Geral da Arquitetura

```text
/look-do-dia ─► generate_ai_looks (025) ─► LOOKS_SCHEMA agora inclui "avaliacao" por look
                    └─ apply_ai_swap(proposta, troca) ─► stylist.apply_swap (em memória)

/looks ─► LookState.evaluate_look(look_id)   (evento background, servidor Reflex)
             │ clima: WardrobeLifeState (024) via get_state · catálogo: StoreState · estilo: perfil
             ▼
          stylist.request_evaluation ─► Claude API (EVALUATION_SCHEMA, structured outputs)
          stylist.validate_evaluation ─► LookReview
             └─ save_adjusted_look ─► LookState.save_look (POST meusLooks existente)
```

Sem endpoints novos: a versão ajustada é um look novo, criado pelo fluxo de criação que já existe, com cache local e sincronização.

## Contratos

- **`EVALUATION_SCHEMA`** (structured outputs): `nota_clima`, `nota_harmonia`, `nota_ocasiao`, `nota_conforto`, `nota_estilo` (inteiro com `enum` 1–5, porque o schema não aceita `minimum`/`maximum`), `pontos_fortes`, `problemas[]`, `trocas[]` com `papel`, `sai_ref`, `entra_origem`, `entra_ref`, `entra_descricao`, `motivo`.
- **Dataclasses de estado:** `LookReview` (notas, `nota_geral` formatada em pt-BR, `problemas`, `trocas`, `disponivel`) e `LookSwap` (`sai_ref`, `sai_nome`, `entra: LookPiece`, `motivo`, `aplicavel`). `LookProposal.avaliacao` é um `LookReview`.

## Validação

- A resolução de peças da 025 foi extraída para `_Inventory.piece`, usada tanto pelas peças do look quanto pela peça que entra em cada troca.
- Nota fora de 1–5 vira 3 (defensivo; o schema já restringe). No máximo 3 trocas e 5 problemas.
- `sai_ref` que não pertence ao look vira acréscimo. A troca é aplicável só se a entrada for do armário ou do catálogo. Nos looks manuais, só entradas do armário podem ser salvas, porque um look guarda chaves do armário.
- `closet_pieces` infere o papel pela categoria do armário (Partes de cima → cima, Vestidos → peça única etc.); também passou a ser usada na sugestão básica.

## Estado e UI

- `WardrobeLifeState.apply_ai_swap(proposal_id, swap_id)`: aplica e reatribui a lista para o Reflex propagar a mudança.
- `LookState`: `review_look_id`, `look_review`, `review_selected_swaps`, `review_loading`, `review_error`, `evaluate_look`, `toggle_review_swap`, `save_adjusted_look`, `close_review`.
- Componentes: `review_summary` (nota geral + cinco notas + pontos fortes + problemas), `swap_description`, `ai_swap_row` (botão Aplicar), `manual_swap_row` (checkbox), `manual_review_panel` (acima da lista em `/looks`), e o botão "Avaliar com IA" em cada `look_card`.

## Decisões

1. **Avaliação na mesma chamada da geração:** não há custo nem latência extra. A instrução pede rigor ("como um segundo estilista"), para reduzir a tendência de autoaprovação.
2. **Versão ajustada em vez de edição:** preserva o original e dispensa endpoint novo no Xano e no SQLite.
3. **Limite compartilhado:** avaliação e geração consomem a mesma cota por hora (`OSDROUPA_AI_LOOKS_PER_HOUR`).
