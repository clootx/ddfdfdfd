# Especificação — Visualização de looks (delta de `ai-stylist`)

## Requisitos Funcionais

### RF-VIS-01 — Composição real
Cada proposta da IA deve exibir um quadro com as fotos das peças. Peças sem foto aparecem com ícone e nome. Peças que não são do armário têm borda tracejada.

### RF-VIS-02 — Imagem gerada sob demanda
Com `GEMINI_API_KEY` configurada, a pessoa pode pedir a imagem de uma proposta. Sem a chave, o botão não aparece e a composição real continua disponível.

### RF-VIS-03 — Fidelidade
O pedido envia as fotos reais disponíveis das peças como referência (até 10) e a descrição de cada peça, a paleta e os tecidos. O prompt exige manequim invisível, peças inteiras, fundo neutro, sem pessoas, sem texto e sem logotipos.

### RF-VIS-04 — Segurança das referências
O servidor só busca imagens remotas por HTTPS, em hosts que resolvem para IPs públicos, sem seguir redirecionamentos, com tipo PNG/JPEG/WebP e até 4 MB. Arquivos locais só são lidos de dentro da pasta `assets/`.

### RF-VIS-05 — Transparência
A imagem gerada é rotulada como gerada por IA (Google Gemini, com marca d'água SynthID), com o aviso de que as peças podem diferir das reais.

### RF-VIS-06 — Limites e erros
Até `OSDROUPA_IMAGES_PER_HOUR` imagens por conta por hora, uma geração por vez por sessão e timeout de 120 s. Cota excedida, recusa, falha do serviço ou resposta sem imagem resultam em mensagem clara, sem alterar a proposta.

---

## Cenários de Aceitação (Gherkin BDD)

### Cenário 1: composição sem chave
- **Dado** que nenhuma chave do Google está configurada,
- **Quando** a IA gera propostas,
- **Então** cada card mostra o quadro com as fotos das peças e nenhum botão de imagem.

### Cenário 2: imagem com referências
- **Dado** uma proposta com três peças do armário que têm foto,
- **Quando** a pessoa clica em "Gerar imagem do look",
- **Então** as três fotos vão como referência e a imagem aparece no card com o rótulo de IA.

### Cenário 3: URL interna bloqueada
- **Dado** uma peça cujo link de imagem aponta para `https://127.0.0.1/` ou para um IP privado,
- **Quando** a imagem do look é gerada,
- **Então** essa foto não é buscada e a peça entra só pela descrição.

### Cenário 4: cota excedida
- **Dado** que a conta já gerou 5 imagens na última hora,
- **Quando** pede outra,
- **Então** recebe o tempo de espera e nenhuma chamada é feita.

### Cenário 5: serviço indisponível
- **Dado** que a API Gemini responde com erro 503,
- **Quando** a pessoa pede a imagem,
- **Então** vê "O serviço de imagens está indisponível no momento." e o card continua igual.
