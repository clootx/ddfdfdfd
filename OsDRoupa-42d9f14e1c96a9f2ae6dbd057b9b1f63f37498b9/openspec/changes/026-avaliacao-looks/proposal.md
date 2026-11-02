# Proposta — 026-avaliacao-looks

> **Atualização (Change 029):** o provedor de IA passou da Claude API (Anthropic) para o Google Gemini (`gemini-3.8-flash`, plano gratuito). As referências à Anthropic, a `ANTHROPIC_API_KEY`, ao modelo `claude-opus-5-5` e a `fallbacks` abaixo são históricas; o restante desta change continua válido. Ver [`029-estilista-gemini`](../029-estilista-gemini/).

## Contexto

A Change 025 gera looks com justificativa, mas não diz o quanto cada combinação atende ao clima, à ocasião, ao conforto e ao estilo, nem aponta o que poderia melhorar. Os looks montados manualmente em `/looks` não recebem nenhuma análise. A API de looks oferece apenas criar, listar e remover (não há edição).

## Objetivo

Avaliar looks (gerados pela IA ou montados pela pessoa) por critérios explícitos, apontar problemas e propor substituições concretas que possam ser aplicadas com um clique.

## Escopo incluído

- Avaliação com notas de 1 a 5 para clima, harmonia, ocasião, conforto e coerência com o estilo, mais a nota geral (média), os pontos fortes e os problemas encontrados.
- Até 3 trocas sugeridas por look, cada uma indicando a peça que sai, a peça que entra (do armário, do catálogo ou sugerida em texto) e o motivo.
- Looks da IA: a avaliação vem na mesma chamada da geração (sem custo extra). "Aplicar troca" substitui a peça na proposta antes de salvar.
- Looks manuais (`/looks`): botão "Avaliar com IA" com o contexto climático da Change 024. Trocas do armário podem ser marcadas e salvas como uma nova versão do look, pelo fluxo de criação existente.
- Validação das trocas contra o armário e o catálogo reais, mesma regra da 025.
- Limite por conta compartilhado com a geração de looks.

## Escopo excluído

- Editar um look salvo no lugar (exigiria endpoint novo no Xano e no SQLite).
- Persistir avaliações.
- Avaliação sem IA (sem chave, o botão informa que o recurso está indisponível).

## Dependências e impactos

- **Modelagem de dados:** nenhuma.
- **APIs:** nenhuma nova; reuso de `meusLooks` (POST) para a versão ajustada.
- **Frontend:** cards da IA em `/look-do-dia`; `LookState` e cards de `/looks`.
- **Integrações externas:** Claude API (já adicionada na 025).
- **Depende de:** 024 e 025.
