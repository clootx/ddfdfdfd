# Design — 014-ai-fashion-catalog-manual-checkout

## Catálogo demonstrativo

Adicionar `PRODUTO.demonstracao` como booleano opcional, tratando `null` como falso para os produtos existentes. Inserir novos registros em modo aditivo com IDs reservados, `Categoria` reconhecida pela loja, `Qtd_Disp=0`, `Precisa_Produzir=true` e descrição que identifica o caráter demonstrativo. Nenhum produto atual será substituído.

As imagens ficam vazias enquanto o gerador não estiver configurado; a loja usa seu placeholder nativo de vestuário. URLs de imagens locais só serão gravadas depois que os arquivos existirem em `assets/`.

## Checkout sem gateway

`POST /checkoutPedidoDemonstrativo` exige `auth=user`, localiza CLIENTE por `$auth.id`, confirma propriedade do endereço, aceita somente produtos `demonstracao=true` e `Precisa_Produzir=true`, valida categorias e quantidades, e recalcula o total com preços do Xano.

A chave de idempotência ganha prefixo próprio para não colidir com o checkout PIX. Uma transação cria PEDIDO e ITEM; `pagamento_status` recebe `Aguardando confirmação da loja`. O endpoint não chama Asaas, não cria TRANSACAO e não baixa estoque. Pedidos repetidos retornam o pedido existente quando endereço e itens coincidem.

O checkout PIX continua disponível para produtos não demonstrativos e mantém suas validações atuais. O endpoint PIX também recusa explicitamente qualquer produto demonstrativo.

## Reflex

Cartões e detalhes mostram o selo `Produto demonstrativo`. A sacola guarda essa marca somente para selecionar a apresentação; o Xano continua sendo a autoridade. Uma sacola apenas demonstrativa chama o endpoint sem gateway e mostra confirmação pendente da loja, sem QR ou texto de pagamento aprovado. Sacolas mistas são recusadas antes do envio.

## Verificação e ativação

Validar os scripts com o CLI Xano, revisar a prévia de records antes de enviar a lista aditiva e compilar o Reflex. A confirmação ponta a ponta exige conta Xano com cliente e endereço associados. Pedidos de demonstração nunca representam pagamento recebido.
