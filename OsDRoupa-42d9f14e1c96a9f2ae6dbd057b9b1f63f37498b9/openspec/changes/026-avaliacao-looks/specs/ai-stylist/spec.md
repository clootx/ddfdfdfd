# Especificação — Avaliação de looks (delta de `ai-stylist`)

## Requisitos Funcionais

### RF-AVAL-01 — Critérios
Toda avaliação deve conter notas inteiras de 1 a 5 para clima, harmonia, ocasião, conforto e estilo, a nota geral (média com uma casa decimal), os pontos fortes e a lista de problemas (pode ser vazia).

### RF-AVAL-02 — Trocas sugeridas
Uma avaliação pode sugerir até 3 trocas. Cada troca indica o papel, a peça que sai (referência de uma peça do look ou vazio para acrescentar), a peça que entra (armário, catálogo ou sugerida) e o motivo.
- Uma troca cujo item de entrada não exista no armário disponível ou no catálogo vira "sugerida" e não pode ser aplicada.
- Uma troca cuja peça de saída não pertença ao look é tratada como acréscimo.

### RF-AVAL-03 — Looks da IA
Cada proposta da 025 traz a sua avaliação. "Aplicar troca" substitui a peça na proposta, remove a troca da lista e recalcula a cobertura. Só trocas com entrada do armário ou do catálogo são aplicáveis.

### RF-AVAL-04 — Looks manuais
Em `/looks`, a pessoa pode pedir a avaliação de um look salvo. O contexto inclui o clima atual (Change 024) ou o clima manual, a ocasião do look e o estilo do perfil. Trocas com entrada do armário podem ser marcadas e salvas como um novo look "(ajustado)"; o original é preservado.

### RF-AVAL-05 — Indisponibilidade e limites
Sem chave, com falha da API ou com o limite por hora atingido, a interface explica o motivo e nada é alterado.

---

## Cenários de Aceitação (Gherkin BDD)

### Cenário 1: avaliação junto com a geração
- **Dado** que a IA gerou looks para uma pessoa em Porto Alegre com 12 °C,
- **Quando** os cards aparecem,
- **Então** cada card mostra as cinco notas, a nota geral, os pontos fortes e os problemas.

### Cenário 2: aplicar troca na proposta
- **Dado** um card com a troca "camiseta → suéter do armário" por causa do frio,
- **Quando** a pessoa clica em "Aplicar",
- **Então** o suéter substitui a camiseta no card e a troca some da lista.

### Cenário 3: troca inválida
- **Dado** que o modelo sugere entrar com uma chave inexistente,
- **Quando** a avaliação é validada,
- **Então** a troca aparece como "peça sugerida", sem botão de aplicar.

### Cenário 4: avaliar look manual
- **Dado** um look salvo em `/looks` com bermuda e regata para "Trabalho",
- **Quando** a pessoa clica em "Avaliar com IA",
- **Então** vê as notas, a ocasião apontada como problema e trocas do próprio armário.

### Cenário 5: salvar versão ajustada
- **Dado** a avaliação de um look manual com duas trocas do armário marcadas,
- **Quando** a pessoa clica em "Salvar versão ajustada",
- **Então** um novo look "(ajustado)" é criado com as peças trocadas e o original continua na lista.

### Cenário 6: sem chave
- **Dado** que `ANTHROPIC_API_KEY` não está configurada,
- **Quando** a pessoa pede a avaliação de um look manual,
- **Então** recebe a mensagem de que a avaliação com IA está indisponível.
