# Design Técnico — 029-estilista-gemini

## Arquitetura

```text
WardrobeLifeState / LookState  (eventos background, servidor Reflex)
        │
        ▼
OSDroupa/ai/stylist.py        prompts, contexto, schemas, validação, trocas (sem SDK)
        │  _structured_call → get_text_provider().generate_json(kind, system, user_text, schema)
        ▼
OSDroupa/ai/providers/__init__.py   TextProvider (Protocol), ProviderError(reason), fábrica
OSDroupa/ai/providers/gemini.py     GeminiTextProvider → genai.Client().aio.interactions.create(...)
```

`imaging.py` continua chamando o Gemini diretamente (é outro tipo de saída), agora atrás de `images_enabled()`.

## Chamada

```python
await client.aio.interactions.create(
    model=GEMINI_MODEL,                       # padrão "gemini-3.8-flash"
    system_instruction=SYSTEM_PROMPT,
    input=json_do_contexto,
    response_format={"type": "text", "mime_type": "application/json", "schema": LOOKS_SCHEMA},
)
texto = interaction.output_text            # validado por _parse_looks + validate_looks
```

Formato confirmado na documentação oficial de saída estruturada e nos tipos do SDK instalado (`TextResponseFormat`: `type`, `mime_type`, `schema`; `Interaction.status` com `completed`, `failed`, `incomplete`…; `system_instruction: str`).

## Schemas

As notas de avaliação passaram de `enum: [1..5]` para `minimum: 1, maximum: 5`. Isso evita depender de suporte a `enum` em inteiros, e a validação local continua limitando os valores a 1–5. A compatibilidade completa dos schemas com o Gemini (incluindo `additionalProperties: false`) só é confirmada pela chamada real da Etapa 8.

## Mapeamento de erros

| Origem | `reason` | Repetir? |
|---|---|---|
| `ClientError` 429 | `quota` | Não |
| `ClientError` 401/403 | `auth` | Não |
| `ClientError` 404 | `not_configured` (modelo indisponível para a chave) | Não |
| outro `ClientError` | `blocked` | Não |
| `ServerError`/`APIError`/rede | `unavailable` | Não |
| `asyncio.wait_for` 90 s | `timeout` | Não |
| status ≠ `completed` | `blocked` | Não |
| `output_text` vazio | `invalid_output` | Uma vez |
| JSON fora do schema | (validação local) | Uma vez |

## Privacidade e custo

- Plano gratuito: conteúdo enviado pode ser usado pelo Google para melhorar produtos (página oficial de preços). O contexto já exclui nome, e-mail, endereço completo, fotos e IDs internos; a observação livre é limitada a 280 caracteres e a interface pede para não incluir dados pessoais.
- Texto: os modelos `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite` e `gemini-3.1-flash-lite` têm plano gratuito. Os limites por modelo aparecem só no painel do AI Studio; a cota diária zera à meia-noite (horário do Pacífico).
- Imagem: sem plano gratuito (cerca de US$ 0,034 por imagem 1K no `gemini-nano-banana-2.1`, segundo resumo da página de preços; conferir antes de ativar).
