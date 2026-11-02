# Proposta — 027-visualizacao-looks

> **Atualização (Change 029):** a geração de imagens agora fica desligada por padrão (`OSDROUPA_IMAGES_ENABLED=false`), pois não há plano gratuito; a chave `GEMINI_API_KEY` sozinha não ativa o recurso. Ver [`029-estilista-gemini`](../029-estilista-gemini/).

## Contexto

Os looks da IA (Changes 025 e 026) aparecem como listas de peças com miniaturas. Não há uma visão do conjunto, nem uma imagem que mostre como o look fica montado. A Change 014 deixou a geração de imagens fora do escopo até haver uma ferramenta autorizada e configurada. Agora foi aprovado o uso da API Gemini do Google.

## Objetivo

Mostrar cada look visualmente de duas formas complementares:
1. **Composição real:** um quadro com as fotos das próprias peças, sem custo, fiel ao acervo.
2. **Imagem editorial gerada pelo Google (Gemini):** o look montado num manequim invisível, usando as fotos reais como referência, sob demanda.

## Escopo incluído

- Quadro de composição em cada proposta da IA: fotos do armário com borda contínua; sugestões do catálogo ou em texto com borda tracejada e marcador.
- Botão "Gerar imagem do look" quando `GEMINI_API_KEY` estiver configurada. A geração é assíncrona, uma por vez por sessão, com limite por conta (`OSDROUPA_IMAGES_PER_HOUR`, padrão 5).
- Envio de até 10 fotos das peças como referência (upload em data URI, assets locais PNG/JPEG/WebP ou links HTTPS públicos de até 4 MB).
- Imagem salva no diretório de uploads do Reflex e exibida com o aviso "Imagem gerada por IA… SynthID".
- Tratamento de erros: sem chave, cota (429), recusa, falha do serviço, timeout, resposta sem imagem.

## Escopo excluído

- Persistir a imagem junto ao look no Xano ou no SQLite (fica para a Change 028, feed).
- Gerar imagens de pessoas ou de rostos; o prompt pede manequim invisível e "sem pessoas".
- Imagens para looks manuais em `/looks` (pode ser estendido depois com o mesmo serviço).
- Ilustrações SVG do catálogo como referência (formato não aceito); essas peças entram só pela descrição.

## Dependências e impactos

- **Modelagem de dados:** nenhuma.
- **APIs:** nenhuma no Xano ou no SQLite.
- **Frontend:** cards da IA em `/look-do-dia`.
- **Integrações externas:** API Gemini do Google, Interactions API (`google-genai==2.34.0`), modelo padrão `gemini-nano-banana-2.1`.
- **Configuração:** `GEMINI_API_KEY` (segredo, só no servidor), `OSDROUPA_IMAGE_MODEL`, `OSDROUPA_IMAGES_PER_HOUR`.
- **Depende de:** 025 (propostas). A composição real funciona sem nenhuma chave.
