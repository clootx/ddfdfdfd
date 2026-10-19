# Proposta — 008-orders-checkout-payments

## Contexto

A Change 007 criou loja e sacola, mas ainda não finaliza pedidos. O Xano possui `PEDIDO`, `ITEM` e `TRANSACAO`, além de integração Asaas antiga que aceita valor livre e não vincula a cobrança a um pedido. Os CRUDs públicos dessas tabelas não validam o cliente autenticado.

## Objetivo

Criar checkout autenticado, histórico e detalhe de pedidos sem confiar em preço, total, cliente ou status enviados pelo navegador.

## Escopo incluído

- Criar `/checkout`, exigir sessão, endereço do próprio cliente e itens válidos.
- Começar com PIX. O estado atual de pedidos do Xano já contempla o fluxo PIX; boleto fica para uma change posterior após revisar os estados e contratos.
- Recalcular preços e disponibilidade no Xano antes de criar pedido ou cobrança.
- Vincular endereço ao pedido e pedido à transação; rejeitar tentativas repetidas por chave de idempotência.
- Criar `/pedidos` e `/pedido?id={id}` com dados filtrados pelo cliente autenticado.
- Exibir código/QR PIX pendente e só mostrar pagamento confirmado após webhook Asaas autenticado.

## Fora do escopo

- Capturar ou persistir dados brutos de cartão no Reflex.
- Marcar pedido como pago ao criar a cobrança.
- Operações de produção, entrega, cancelamento ou estorno.
- Publicar alterações no Xano ou alterar catálogo remoto nesta etapa.

## Dependências e riscos

- O catálogo Xano consultado na Change 007 ainda contém comidas e bebidas. A loja não deve receber compras reais até trocar esses registros por roupas.
- A integração Asaas atual não vincula pedido e transação e não devolve instrução PIX. Ela não será chamada pelo frontend.
- As alterações de modelo e APIs Xano precisam ser importadas, revisadas e validadas no workspace antes de habilitar pedidos reais.
