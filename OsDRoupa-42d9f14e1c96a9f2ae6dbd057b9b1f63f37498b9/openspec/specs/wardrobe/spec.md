# Especificação consolidada — Armário

## RF-WARD-01: Privacidade

Cada peça pertence ao cliente derivado da sessão autenticada; leitura e remoção respeitam esse vínculo.

## RF-WARD-02: Sincronização

O Xano é a fonte de verdade quando disponível. Cache local é separado por conta e usado como suporte offline; itens legados migram uma única vez por chave idempotente.

## RF-WARD-03: Operações

Pessoa autenticada pode consultar, adicionar e remover peças pessoais, sem enviar `cliente_id` como autoridade.

## RF-WARD-04: Indisponibilidade

Falhas de rede preservam cache local e exibem um aviso de que as alterações não estão sincronizadas.
