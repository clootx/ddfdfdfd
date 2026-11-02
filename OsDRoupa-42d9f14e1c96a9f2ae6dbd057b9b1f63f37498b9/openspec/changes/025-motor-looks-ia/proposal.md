# Proposta — 025-motor-looks-ia

> **Atualização (Change 029):** o provedor de IA passou da Claude API (Anthropic) para o Google Gemini (`gemini-3.8-flash`, plano gratuito). As referências à Anthropic, a `ANTHROPIC_API_KEY`, ao modelo `claude-opus-5-5` e a `fallbacks` abaixo são históricas; o restante desta change continua válido. Ver [`029-estilista-gemini`](../029-estilista-gemini/).

## Contexto

O endpoint `lookDoDia` escolhe até quatro peças por regras fixas (estação da peça × categoria de clima × ocasião), sem explicar a escolha, sem considerar cores, tecidos, proporção, estilo da pessoa ou acessórios, e sem oferecer alternativas. A Change 024 passa a fornecer contexto climático real. O perfil já guarda `estilo_preferido`, e o armário guarda categoria, cor, estação e estado de uso das peças.

## Objetivo

Gerar, no servidor Reflex e com a Claude API, várias propostas de looks completos a partir do contexto real (clima, região, data/hora, ocasião e estilo) e das peças disponíveis, cada uma com justificativa, e garantir que nenhuma peça inexistente seja apresentada como se estivesse no armário.

## Escopo incluído

- Serviço `OSDroupa/ai/stylist.py` que monta o contexto, chama a Claude API com saída estruturada (`output_config.format` com JSON schema) e valida a resposta.
- De 3 a 5 looks por pedido. Cada look traz nome, peças (parte de cima, parte de baixo ou peça única, calçado, camada opcional, acessórios), paleta de cores, tecidos recomendados, justificativa climática, justificativa de estilo e ocasião, e nível de conforto.
- Peças referenciadas por `chave_local` do armário. Itens do catálogo da loja podem completar o look, marcados como "sugestão de compra". Peças que não existem em nenhum dos dois só aparecem como "peça sugerida", em texto, nunca como item do armário.
- Exclusão de peças com estado "Suja" ou "Lavando".
- Campo opcional de observação livre (ex.: "reunião com cliente, vou de metrô"), com limite de tamanho.
- Fallback automático para a heurística atual de `lookDoDia` quando `ANTHROPIC_API_KEY` não estiver configurada ou a API falhar.
- Limite de gerações por conta (padrão: 10 por hora) e timeout.
- Salvar uma proposta em Meus Looks pelo endpoint existente `meusLooks`.

## Escopo excluído

- Avaliação por critérios e substituição de peças (Change 026).
- Imagens dos looks (Change 027).
- Feed e persistência dos looks gerados (Change 028).
- Tendências em tempo real a partir da web; o modelo usa conhecimento próprio, e a interface não apresenta tendências como notícia.
- Endpoints de IA no Xano: a decisão aprovada mantém a lógica de IA no servidor Reflex.

## Dependências e impactos

- **Modelagem de dados:** nenhuma tabela nova. Leitura de `ROUPA_CLIENTE`, do perfil (`estilo_preferido`) e do catálogo (`produto`).
- **APIs:** sem endpoints novos no Xano ou no SQLite. Reuso de `meuArmario`, `perfil`/`buscaCliente`, `produto` e `meusLooks`.
- **Frontend:** `WardrobeLifeState` e `/look-do-dia` (lista de propostas no lugar de uma única combinação).
- **Integrações externas:** Claude API (SDK oficial `anthropic`, nova dependência em `requirements.txt`).
- **Configuração:** `ANTHROPIC_API_KEY` (segredo, só no servidor), `OSDROUPA_AI_MODEL` (padrão `claude-opus-5-5`), `OSDROUPA_AI_LOOKS_PER_HOUR` (padrão 10).
- **Depende de:** Change 024 (contexto climático). Sem ela, o contexto usa a escolha manual de clima.
