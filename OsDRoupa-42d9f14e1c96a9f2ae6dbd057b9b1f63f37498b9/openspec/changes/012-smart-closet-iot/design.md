# Design — 012-smart-closet-iot

## Modelo e rascunhos Xano locais

`DISPOSITIVO_ARMARIO` pertence a `CLIENTE` e guarda identificador privado, tipo, versão, estado, chave pública e data do último contato. A chave privada de assinatura permanece no hardware e nunca é enviada ao navegador ou armazenada no Xano.

`PAREAMENTO_DISPOSITIVO` guarda somente o hash do código temporário, o cliente solicitante, a expiração e a data de consumo. `EVENTO_DISPOSITIVO` registra leituras validadas e uma chave idempotente única por dispositivo.

Os schemas locais estão em `xano/table/dispositivo_armario.xs`, `xano/table/pareamento_dispositivo.xs` e `xano/table/evento_dispositivo.xs`. Os GET privados da lista e do detalhe têm rascunhos locais. Pareamento e ingestão assinada continuam pendentes de implementação e validação no workspace. Nenhum arquivo foi importado ou publicado.

## Contratos Xano planejados

| Rota | Acesso | Regra |
|---|---|---|
| `GET /meusDispositivos` | `auth=user` | Lista apenas dispositivos do cliente autenticado |
| `POST /solicitarPareamento` | `auth=user` | Gera código temporário com fonte criptograficamente segura e armazena somente o hash |
| `POST /confirmarPareamento` | `auth=user` + código | Consome o código atomicamente uma única vez e vincula o dispositivo ao cliente solicitante |
| `GET /meuDispositivo/{id}` | `auth=user` | Retorna detalhe e eventos apenas do proprietário |
| `POST /eventosDispositivo` | assinatura do dispositivo | Valida assinatura, timestamp e idempotência antes de gravar evento |

## Reflex

As páginas privadas `/dispositivos`, `/dispositivos/conectar` e `/dispositivo?id=...` validam a sessão antes de consultar Xano. A lista vazia explica que não há dispositivo conectado; endpoint ausente informa que a integração não foi publicada. Os estados `conectado`, `pareamento_pendente` e `sem_contato` são exibidos sem inventar telemetria.

## Segurança e privacidade

- Códigos expiram, são de uso único e pertencem à conta que iniciou o pareamento.
- A chave privada de assinatura permanece no dispositivo; o Xano valida eventos com a chave pública registrada.
- Eventos precisam de assinatura e timestamp válidos e chave idempotente. Repetições e origens inválidas são recusadas.
- O cliente não pode transferir, consultar ou remover dispositivos de outra conta.
- Telemetria retém apenas campos necessários e mostra unidade e horário.

## Verificação

Validar sessão, propriedade do dispositivo, expiração e reuso do código, assinatura, eventos repetidos, unidade e estado sem hardware no workspace Xano e com equipamento real. A implementação de assinatura depende de confirmar no workspace Xano uma primitiva compatível com a chave pública escolhida.