# Especificação — Provedor Gemini do estilista (delta de `ai-stylist`)

## Requisitos Funcionais

### RF-PROV-01 — Provedor configurável
O estilista deve obter o provedor de texto por configuração (`OSDROUPA_AI_PROVIDER`, padrão `gemini`). Um provedor desconhecido torna a IA indisponível com mensagem clara, sem quebrar a página.

### RF-PROV-02 — Gemini
Com `GEMINI_API_KEY` configurada, o estilista usa o modelo `GEMINI_MODEL` (padrão `gemini-3.8-flash`) pela Interactions API, pedindo JSON conforme o schema do look ou da avaliação.

### RF-PROV-03 — Erros sem desperdício de cota
Cota esgotada (429), autenticação recusada (401/403), modelo indisponível (404), pedido recusado, status diferente de `completed`, falha de rede e timeout resultam em mensagem segura e no plano B (sugestão básica). Só a resposta vazia ou fora do formato é repetida, uma única vez.

### RF-PROV-04 — Segredos e logs
A chave fica apenas no servidor; nunca aparece no bundle do frontend nem nos logs. Os logs registram tipo de chamada, modelo, status, duração e contagem de tokens.

### RF-PROV-05 — Imagens pagas desligadas
A geração de imagens só fica disponível com `OSDROUPA_IMAGES_ENABLED=true` **e** chave configurada. Sem a ativação, o botão não aparece e nenhuma chamada de imagem é feita.

### RF-PROV-06 — Privacidade
A política de privacidade informa os dados enviados ao Google e que, no plano gratuito, o conteúdo pode ser usado para melhorar os produtos do Google.

---

## Cenários de Aceitação (Gherkin BDD)

### Cenário 1: sem chave
- **Dado** que `GEMINI_API_KEY` não está definida,
- **Quando** a pessoa pede looks,
- **Então** recebe a sugestão básica com o aviso de que a IA está indisponível, e nenhuma chamada externa é feita.

### Cenário 2: cota gratuita esgotada
- **Dado** que o Gemini responde 429,
- **Quando** a pessoa pede looks,
- **Então** vê que a cota gratuita foi atingida, recebe a sugestão básica e a chamada não é repetida.

### Cenário 3: imagem desligada por padrão
- **Dado** que a chave está configurada e `OSDROUPA_IMAGES_ENABLED` não foi definida,
- **Quando** a IA gera propostas,
- **Então** o botão de imagem não aparece e nenhuma chamada de imagem é feita.

### Cenário 4: troca de modelo
- **Dado** `GEMINI_MODEL=gemini-3.6-flash`,
- **Quando** a pessoa pede looks,
- **Então** a chamada usa esse modelo.
