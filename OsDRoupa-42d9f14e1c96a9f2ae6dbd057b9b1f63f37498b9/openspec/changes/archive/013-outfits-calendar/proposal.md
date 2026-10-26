# Proposta — 013-outfits-calendar

## Contexto

O armário digital já permite organizar peças, mas ainda não transforma o acervo em looks reutilizáveis nem em um planejamento visual para a semana. O progresso local deve continuar disponível quando o Xano estiver fora do ar.

## Objetivo

Criar montagem de looks com peças próprias e um calendário pessoal que mostre combinações planejadas, com persistência local por conta e sincronização idempotente preparada no Xano.

## Escopo incluído

- Criar looks com nome, ocasião, peças do armário e data opcional.
- Exibir os looks salvos e os looks planejados por data em páginas responsivas.
- Salvar, migrar e remover looks no Xano somente para a conta autenticada.
- Manter cache local separado por conta quando a API remota estiver indisponível.

## Fora do escopo

- Feed social, compartilhamento público e recomendações automáticas por IA ou clima.
- Sincronização com Google Calendar ou Outlook.
- Alterar o estado de uso da peça automaticamente ao criar ou usar um look.

## Critérios de aceite

- Um look exige nome e ao menos uma peça disponível no armário da conta.
- A mesma chave local não cria looks duplicados durante migração ou repetição de requisição.
- A agenda lista apenas looks com data e os dados ficam associados ao usuário autenticado.
- Sem rede ou API publicada, o cache continua visível e a interface informa o estado de sincronização.
