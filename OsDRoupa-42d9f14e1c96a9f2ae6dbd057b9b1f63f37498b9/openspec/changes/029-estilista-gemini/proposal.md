# Proposta — 029-estilista-gemini

## Contexto

As Changes 025 e 026 implementaram o estilista com a Claude API (Anthropic). A decisão do projeto mudou: a IA usada pelas pessoas na plataforma deve ser o **Google Gemini**, priorizando o acesso gratuito, sem dependência da Anthropic ou da OpenAI. A geração de imagens da 027 já usava o Gemini, mas é paga (não há plano gratuito) e hoje seria ativada apenas pela presença da `GEMINI_API_KEY`, o que pode gerar cobrança em um projeto com faturamento ativo.

## Objetivo

Trocar o provedor do estilista para o Gemini, manter a arquitetura pronta para outros provedores e impedir chamadas pagas sem ativação explícita.

## Escopo incluído

- Camada de provedor (`OSDroupa/ai/providers/`): interface `TextProvider` e erro `ProviderError` com motivo classificado (`quota`, `auth`, `blocked`, `invalid_output`, `timeout`, `unavailable`, `not_configured`).
- Provedor Gemini com o SDK oficial `google-genai` e a Interactions API, saída JSON com schema, `GEMINI_API_KEY` e `GEMINI_MODEL` (padrão `gemini-3.8-flash`, que tem plano gratuito).
- `stylist.py` sem SDK: só prompts, contexto, validação e trocas. Nova tentativa apenas para resposta fora do formato; erros de cota/autenticação/bloqueio não são repetidos.
- Remoção completa da Anthropic: dependência, código, variáveis e textos da interface.
- `OSDROUPA_IMAGES_ENABLED=false` por padrão; a chave sozinha não liga a geração de imagens.
- Política de privacidade e `.env.example` atualizados com o aviso de uso de dados no plano gratuito.

## Escopo excluído

- Limites persistentes de uso (Etapa 4 / esta change, tarefa seguinte).
- Personalização e feedback (Change 030).
- Chamada real à API (autorizada apenas na Etapa 8, uma única vez, no plano gratuito).

## Dependências e impactos

- **Dependências:** remove `anthropic`; mantém `google-genai==2.34.0`.
- **Configuração:** `OSDROUPA_AI_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `OSDROUPA_IMAGES_ENABLED`. Removidos `ANTHROPIC_API_KEY` e `OSDROUPA_AI_MODEL`.
- **Substitui:** as decisões de provedor e de modelo dos designs da 025 e da 026 (o restante delas continua válido).
