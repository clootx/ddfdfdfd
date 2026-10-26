# Especificação — Looks e calendário pessoal

## RF-LOOK-01: Montagem de look

Pessoa autenticada pode nomear um look, escolher uma ocasião e compor o look com uma ou mais peças disponíveis no próprio armário.

### Cenário: composição válida
- **Dado** que a pessoa está autenticada e possui peças no armário
- **Quando** informa um nome e seleciona ao menos uma peça
- **Então** o look aparece em sua lista e pode receber uma data planejada

### Cenário: composição incompleta
- **Dado** que a pessoa não informou nome ou não selecionou peças
- **Quando** tenta salvar
- **Então** a interface explica o que falta e não cria um look vazio

## RF-LOOK-02: Privacidade e sincronização

O Xano deriva o proprietário da sessão, valida cada peça referenciada e retorna apenas looks da conta autenticada. A chave local torna a migração idempotente.

### Cenário: peça de outra conta
- **Dado** que uma chave de peça não pertence ao cliente autenticado
- **Quando** a pessoa tenta criar um look que a inclui
- **Então** o Xano recusa a operação sem revelar os dados da peça alheia

## RF-LOOK-03: Planejamento

Uma data planejada é opcional. A página de calendário exibe somente looks datados, em ordem cronológica, e a lista completa mantém looks sem data.

### Cenário: agenda sem looks
- **Dado** que a pessoa ainda não planejou looks
- **Quando** abre o calendário
- **Então** encontra um estado vazio com acesso para montar o primeiro look

## RF-LOOK-04: Indisponibilidade

Falha de rede preserva looks por conta no navegador e informa que a sincronização está pendente.
