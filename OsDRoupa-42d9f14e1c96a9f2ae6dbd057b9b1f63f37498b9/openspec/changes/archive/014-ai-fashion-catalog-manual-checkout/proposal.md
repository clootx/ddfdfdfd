# Proposta — 014-ai-fashion-catalog-manual-checkout

## Contexto

A loja oculta os 15 produtos atuais porque o catálogo remoto contém alimentos e bebidas. O checkout disponível exige Asaas e não funciona quando as credenciais do gateway não estão configuradas.

## Objetivo

Permitir demonstrar a loja com produtos de moda criados por IA e enviar pedidos de demonstração sem cobrar o cliente nem marcar pagamento como concluído.

## Escopo incluído

- Identificar produtos demonstrativos no schema para impedir que sejam tratados como mercadoria real.
- Cadastrar um pequeno catálogo demonstrativo por inserção aditiva, preservando os registros atuais.
- Criar checkout autenticado para solicitação de pedido demonstrativo, com preço recalculado no Xano, validação de propriedade do endereço e idempotência.
- Mostrar claramente no Reflex quando um produto e um pedido são demonstrativos.
- Criar o pedido como pendente de confirmação da loja, sem cobrança Asaas, transação financeira ou baixa de estoque.

## Fora do escopo

- Declarar os produtos gerados como mercadoria real, estoque disponível ou preço comercial aprovado.
- Simular confirmação de pagamento, emitir comprovante ou criar dados falsos de transação.
- Alterar ou remover produtos existentes.
- Ativar pagamento online real sem credenciais Asaas e validação no sandbox.
- Gerar imagens raster enquanto a ferramenta de imagem não estiver autorizada e configurada.

## Critérios de aceite

- Produtos demonstrativos aparecem na loja com identificação e descrição transparentes.
- PIX é recusado pelo servidor para produtos demonstrativos.
- O pedido demonstrativo exige sessão e endereço do próprio cliente e usa preço atual do Xano.
- Repetir a mesma chave não cria pedido ou itens duplicados.
- O pedido fica pendente de confirmação da loja e não cria cobrança nem transação.
