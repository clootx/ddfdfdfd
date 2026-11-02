# Especificação — Contexto climático

## Requisitos Funcionais

### RF-CLIMA-01 — Localização
O sistema deve determinar a localização a partir da cidade e UF do endereço padrão da conta autenticada.
- A pessoa pode informar outra cidade brasileira na tela sem alterar o endereço cadastrado.
- A busca da cidade deve ser restrita ao Brasil (`countryCode=BR`), usando a UF para desempate.

### RF-CLIMA-02 — Previsão real
O sistema deve consultar a previsão atual e a do dia da localização e expor um contexto normalizado com temperatura, sensação térmica, mínima e máxima, probabilidade e volume de chuva, umidade relativa, vento, índice UV, condição, data e hora local, período do dia, estação do hemisfério sul e região brasileira.
- O horário usa o fuso da localização (`timezone=auto`).
- A estação não substitui a previsão; ambas fazem parte do contexto.

### RF-CLIMA-03 — Classificação compatível
O sistema deve derivar uma das categorias Quente, Ameno, Frio ou Chuvoso a partir da previsão, para uso pela heurística atual de `lookDoDia`.
- Chuvoso quando a probabilidade de chuva nas próximas 6 horas for ≥ 60% ou houver precipitação atual.
- Caso contrário, a categoria segue a sensação térmica: Quente ≥ 27 °C, Frio ≤ 17 °C, Ameno entre esses valores.

### RF-CLIMA-04 — Transparência
A interface deve mostrar a cidade, a fonte (Open-Meteo) e o horário da consulta, e deixar claro quando o clima foi escolhido manualmente.

### RF-CLIMA-05 — Indisponibilidade
Se não houver endereço, a cidade não for encontrada ou a API falhar ou demorar mais que o limite, o sistema deve manter a escolha manual atual e explicar o motivo, sem bloquear a sugestão de look.

### RF-CLIMA-06 — Cache
Consultas para a mesma localização em até 30 minutos devem reutilizar o resultado em cache no servidor.

---

## Cenários de Aceitação (Gherkin BDD)

### Cenário 1: clima real a partir do endereço padrão
- **Dado** que a pessoa está autenticada e tem endereço padrão em Recife/PE,
- **Quando** abre `/look-do-dia`,
- **Então** vê temperatura, sensação térmica, chuva e umidade de Recife, com fonte e horário, e a categoria correspondente já selecionada.

### Cenário 2: diferenças regionais
- **Dado** duas contas com endereço padrão em Manaus/AM e em Porto Alegre/RS,
- **Quando** cada uma abre `/look-do-dia` no mesmo momento,
- **Então** cada contexto mostra a região e a previsão da própria cidade.

### Cenário 3: cidade informada manualmente
- **Dado** que a pessoa informa "Curitiba" na busca de cidade,
- **Quando** confirma,
- **Então** o contexto passa a ser de Curitiba/PR e o endereço cadastrado não é alterado.

### Cenário 4: sem endereço padrão
- **Dado** que a conta não tem endereço padrão,
- **Quando** abre `/look-do-dia`,
- **Então** vê um convite para informar a cidade e pode continuar com a escolha manual de clima.

### Cenário 5: API indisponível
- **Dado** que a Open-Meteo não responde dentro do tempo limite,
- **Quando** a página tenta carregar o clima,
- **Então** a escolha manual é mantida, uma mensagem informa que a previsão está indisponível e a combinação continua podendo ser gerada.

### Cenário 6: cidade inexistente
- **Dado** que a pessoa informa um nome que não corresponde a nenhuma cidade brasileira,
- **Quando** confirma,
- **Então** recebe a mensagem "Não encontramos essa cidade no Brasil" e o contexto anterior é preservado.
