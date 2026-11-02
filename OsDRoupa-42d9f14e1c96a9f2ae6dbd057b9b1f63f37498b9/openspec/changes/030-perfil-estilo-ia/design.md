# Design — 030-perfil-estilo-ia

- `stylist.build_style_profile(cores, uso, feedback, armario)` monta o resumo; partes vazias são omitidas. Mapeia o `id` do histórico de uso para a `chave` da peça.
- `generate_ai_looks` lê `historicoUso` e `feedbackLooks` só se `personalizacao_ia` não for `false`; falha nessas leituras vira lista vazia e não impede a geração.
- O prompt orienta: preferir as cores favoritas sem se limitar, incluir ao menos um look com peças pouco usadas, não apoiar tudo nas mais usadas, corrigir os motivos dos rejeitados.
- Motivos de 👎 (lista fechada, igual no SQLite, no Xano e na interface): Não combina comigo; Não serve para o clima; Não serve para a ocasião; Pouco confortável; Já uso muito essas peças; Outro motivo. Lista fechada evita texto livre com dados pessoais indo ao modelo.
- Coluna `ai_personalization INTEGER NOT NULL DEFAULT 1` adicionada pela migração aditiva existente; bancos antigos ficam com a personalização ativa.
- No Xano, `CLIENTE.personalizacao_ia` (padrão `true`) e tabela `FEEDBACK_LOOK`.
