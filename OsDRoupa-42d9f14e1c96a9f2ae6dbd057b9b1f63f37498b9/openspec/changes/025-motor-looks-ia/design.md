# Design Técnico — 025-motor-looks-ia

## Visão Geral da Arquitetura

```text
/look-do-dia ─► WardrobeLifeState.generate_ai_looks (evento background, servidor Reflex)
                  │ peças disponíveis (meuArmario), estilo (perfil), catálogo (produto), WeatherContext (024)
                  ▼
             OSDroupa/ai/stylist.py
                  ├─ build_prompt_context(...)   → dict sem dados pessoais
                  ├─ request_looks(...)          → AsyncAnthropic().beta.messages.create(output_config.format=json_schema, fallbacks="default")
                  ├─ validate_looks(...)         → confere chaves do armário e IDs do catálogo, cobertura mínima
                  └─ heuristic_proposal(...)     → converte o resultado de GET lookDoDia (comportamento atual)
```

Xano e SQLite não mudam: continuam fornecendo os dados e persistindo o look salvo (`POST meusLooks`). A IA roda somente no servidor Reflex, conforme a decisão aprovada. O catálogo vem de `StoreState` (via `get_state`), reaproveitando a normalização e o cache da loja.

## Chamada à Claude API

- SDK oficial `anthropic==2.3.0` (cliente assíncrono, `timeout=90 s`, `max_retries=1`). Modelo definido por `OSDROUPA_AI_MODEL`, padrão `claude-opus-5-5`, com `effort: "medium"` (o padrão desse modelo) para equilibrar a qualidade e o tempo de resposta. `claude-sonnet-5-5` pode ser configurado para reduzir custo.
- **Por que não `tool_choice` forçado:** `claude-opus-5-5` e `claude-sonnet-5-5` devolvem erro 400 para `tool_choice` `any`/`tool`. Por isso a saída é garantida por **structured outputs** (`output_config.format` com `json_schema`), que garante JSON válido no primeiro bloco de texto.
- **Recusas:** `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`) re-executa no servidor da Anthropic um pedido recusado por classificador de segurança. Se a cadeia inteira recusar (`stop_reason == "refusal"`), usa a heurística.
- **System prompt:** papel de estilista brasileiro, regras de integridade (só usar chaves fornecidas, marcar sugestões), cobertura mínima, pt-BR, consideração regional e climática. A observação do usuário vai no campo `observacao_usuario` do JSON de contexto e é declarada como dado.
- **Schema da saída** (enums de `papel`, `origem` e `conforto`; todos os objetos com `additionalProperties: false`):

```json
{
  "looks": [{
    "nome": "string",
    "pecas": [{"papel": "cima|baixo|peca_unica|calcado|camada|acessorio|bolsa|oculos|chapeu|relogio",
               "origem": "armario|catalogo|sugerida",
               "ref": "chave_local | produto_id | null",
               "descricao": "string"}],
    "paleta": ["string"],
    "tecidos": ["string"],
    "justificativa_clima": "string",
    "justificativa_estilo": "string",
    "conforto": "baixo|medio|alto"
  }]
}
```

- `max_tokens=16000`. Uma nova tentativa se o JSON não tiver looks; depois disso, fallback. Erros tratados por classe (`RateLimitError`, `AuthenticationError`, `APITimeoutError`, `APIConnectionError`, `APIStatusError`) e convertidos em `StylistUnavailable` com mensagem segura.
- O contexto envia no máximo 120 peças do armário e 40 produtos com estoque ou sob encomenda (id, nome, categoria, tipo, cores, material), para controlar tokens.
- No estado Reflex, as propostas são `dataclasses` tipadas (`LookProposal` / `LookPiece`) para permitir `rx.foreach` sobre as peças.

## Contrato interno — `LookProposal` (estado Reflex)

```python
{"id": "uuid", "nome": str, "pecas": [{"papel", "origem", "ref", "descricao", "imagem_url", "valida": bool}],
 "paleta": [str], "tecidos": [str], "justificativa_clima": str, "justificativa_estilo": str,
 "conforto": str, "precisa_pecas": bool, "fonte": "ia" | "heuristica"}
```

## Modelo de Estado e UI (Reflex)

- **Estado (`WardrobeLifeState`):** `ai_proposals: list[dict]`, `ai_note: str`, `ai_loading: bool`, `ai_notice: str`, `ai_source: str`.
- **Eventos:** `generate_ai_looks` (`@rx.event(background=True)`, para não bloquear a interface durante a chamada), `set_ai_note` (corta em 280 caracteres), `save_ai_proposal(id)` (reaproveita a lógica de `save_daily_look`).
- **UI:** campo "Algo a considerar?", botão "Gerar looks", cards por proposta (miniaturas das peças do armário, selos "do seu armário" / "sugestão de compra" / "peça sugerida", paleta em chips, tecidos, justificativas, conforto), botão "Salvar em Meus Looks" e rodapé indicando se a sugestão veio da IA ou é básica.
- O botão atual "Criar combinação" é mantido como fallback visível.

## Limites e observabilidade

- Contador em memória por `cliente_id`, janela deslizante de 1 h. Por ser por processo, um deploy com várias instâncias exigirá contador compartilhado (pendência registrada).
- Log apenas com metadados: duração, modelo, tokens de entrada e saída, quantidade de looks válidos e número de referências inválidas rebaixadas. Nunca prompt completo, chave ou dados pessoais.

## Decisões Arquiteturais e Integridade

1. **IA no servidor Reflex (aprovado):** evita duplicar a integração em XanoScript e SQLite, e mantém o segredo fora do navegador, porque os eventos Reflex rodam no servidor.
2. **Tool use forçado com schema:** garante JSON parseável e validável, em vez de texto livre.
3. **Validação pós-modelo obrigatória:** o modelo pode inventar referências. A verificação contra as chaves reais é o que garante a integridade.
4. **Fallback para a heurística existente:** a funcionalidade nunca fica indisponível por falta de chave ou por falha do provedor, mesmo princípio do Mercado Pago no `.env.example`.
5. **Minimização de dados:** só cidade/UF e atributos das peças saem do servidor.
6. **Tendências:** o modelo tem data de corte de conhecimento. A interface não afirma "tendência atual"; uma lista editorial de tendências gerenciável pode ser proposta em change futura.
