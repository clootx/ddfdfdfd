# Design — 020-armario-vivo-loyalty-mercadopago

## Arquitetura

Reflex mantém os componentes e estados da interface. As operações passam pelo adaptador HTTP já existente (`XanoAsyncClient`), que encaminha contratos `api:6LtoY7Zt` para o backend SQLite no modo padrão. O modo Xano continua selecionável, mas os novos contratos locais precisam ser publicados no workspace antes de serem usados nesse modo.

O SQLite recebe tabelas de registros de uso, viagens, pedidos de alfaiataria, depoimentos, solicitações de privacidade e campos opcionais de preço de aquisição da peça. Todas as leituras e mutações derivam o usuário do token Bearer; a moderação depende de papel admin.

## Recomendações e planejamento

- Look do dia é determinístico e baseado nas peças ativas, clima e ocasião escolhidos pela pessoa. Não depende de IA nem de localização.
- Mala guarda destino, datas, ocasião e chaves locais das peças pertencentes ao usuário.
- O provador de combinações é uma composição visual das imagens cadastradas, sem gerar uma imagem corporal.
- Cada uso cria um evento por peça; custo por uso é mostrado apenas quando o valor de compra foi informado.
- Conclusões de desafios já possuem chave única por conta/desafio. Pontos são derivados desse registro e do catálogo autorizado de desafios, evitando créditos duplicados ou pontos arbitrários enviados pelo navegador.

## Checkout Mercado Pago

Usar Checkout Pro via Orders API (`POST /v1/orders`), `processing_mode=manual`, cabeçalho `X-Idempotency-Key` e redirecionamento pela URL `checkout_url`. O servidor recalcula os itens e o valor, mantém a reserva de estoque e persiste a referência da Order. O token nunca chega ao navegador.

O webhook recebe o tópico `orders`, valida `x-signature`/`x-request-id`/`data.id` com HMAC-SHA256 e janela de tempo, consulta `GET /v1/orders/{id}` usando o Access Token e confere referência externa e total antes de confirmar pagamento. Repetições são idempotentes. As URLs de retorno não confirmam pagamento.

Variáveis: `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_WEBHOOK_SECRET`, `OSDROUPA_PUBLIC_URL`. Webhooks de Orders são configurados no painel do Mercado Pago. Credenciais de teste e URL HTTPS pública são necessárias para validar o fluxo ponta a ponta. O modo demonstrativo não cria cobrança.

## Depoimentos e privacidade

Depoimentos ficam pendentes até ação administrativa. Só relatos autenticados e acompanhados de consentimento de publicação podem entrar na vitrine; a pessoa pode escolher nome público ou anonimato. Pedidos de titular ficam associados à conta, disponíveis ao titular e à gestão.

A política separa o ambiente local SQLite do Xano configurado, explica o uso do Mercado Pago no checkout e SMTP quando habilitado, e lista dados tratados, finalidade, retenção operacional e canal de solicitação. O texto é informativo e requer revisão do controlador antes de publicação externa.
