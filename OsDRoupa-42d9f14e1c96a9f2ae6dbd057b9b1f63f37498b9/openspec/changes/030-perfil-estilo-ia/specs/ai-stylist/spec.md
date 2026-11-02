# Requisitos — Perfil de estilo e feedback (Change 030)

## ADDED Requirements

### Requirement: Personalização com dados mínimos
Com a personalização ativa, o contexto enviado à IA SHALL incluir `perfil_estilo` com no máximo: cores favoritas, até 5 peças mais usadas, até 5 pouco usadas, até 5 looks aprovados e até 5 rejeitados com motivo, sempre por chave de peça disponível no armário. Tamanhos, nome, e-mail, telefone e endereço SHALL NOT ser enviados.

#### Scenario: Peça suja ou de outra conta
- **WHEN** o histórico cita uma peça suja, lavando ou que não está no armário
- **THEN** ela não aparece no `perfil_estilo`

### Requirement: Opção de desligar
A pessoa SHALL poder desligar a personalização no perfil. Desligada, o contexto SHALL NOT conter `perfil_estilo` nem o estilo preferido, e os botões de avaliação SHALL ficar ocultos.

#### Scenario: Salvar o perfil sem o campo
- **WHEN** o perfil é salvo sem `personalizacao_ia`
- **THEN** a escolha anterior é mantida

### Requirement: Feedback explícito
O feedback SHALL ser gravado somente por clique em 👍 ou 👎. 👎 SHALL exigir um motivo da lista fechada; 👍 não guarda motivo. Chaves de peças que não pertencem à conta SHALL ser descartadas.

#### Scenario: Apagar histórico
- **WHEN** a pessoa pede para apagar o histórico de avaliações
- **THEN** todas as avaliações da conta são removidas e as de outras contas permanecem
