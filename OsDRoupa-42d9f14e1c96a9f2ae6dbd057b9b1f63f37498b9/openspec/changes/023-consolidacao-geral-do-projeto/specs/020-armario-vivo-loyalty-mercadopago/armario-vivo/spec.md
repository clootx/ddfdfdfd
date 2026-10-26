# Especificação: armário vivo, fidelidade e confiança

## Look do dia

### RF-ARM-01 — Recomendar e salvar combinação

O sistema deve combinar peças do armário de acordo com clima e ocasião selecionados, explicar que a recomendação usa apenas o acervo cadastrado e permitir salvá-la como look.

#### Cenário: sugestão com acervo
- **Dado** que a conta tem peças disponíveis no armário
- **Quando** a pessoa informa clima e ocasião
- **Então** o sistema apresenta uma combinação com peças próprias e permite salvá-la

## Uso, mala e provador

### RF-ARM-02 — Histórico e custo por uso

O sistema deve registrar o uso de uma peça pertencente à conta e exibir quantidade de usos. O custo por uso só aparece se a pessoa informar o preço de aquisição.

#### Cenário: peça com preço conhecido
- **Dado** que uma peça tem preço de aquisição e registros de uso
- **Quando** a pessoa abre o histórico
- **Então** o sistema exibe o valor dividido pelo número de usos, sem estimar preço ausente

### RF-ARM-03 — Mala por viagem

O sistema deve salvar listas de viagem e aceitar somente peças pertencentes à conta autenticada.

#### Cenário: salvar mala
- **Dado** que a pessoa seleciona peças próprias, destino e período
- **Quando** salva a viagem
- **Então** a lista permanece associada à conta e pode ser reaberta

### RF-ARM-04 — Provador de combinações

O sistema deve exibir uma composição com fotos das peças cadastradas e identificar o recurso como painel de combinação, sem afirmar que simula caimento no corpo.

### RF-ARM-05 — Foto enviada ou imagem externa

O cadastro de uma peça deve aceitar uma imagem JPG, PNG ou WebP enviada pela pessoa ou um link HTTPS direto para um arquivo de imagem. No backend SQLite, o arquivo enviado deve ficar persistido junto à peça e isolado pela conta autenticada; o cache do navegador não deve armazenar o arquivo. O formulário deve limitar o upload a 2 MB, mostrar uma prévia e explicar que links para páginas de produtos podem não ser imagens diretas.

#### Cenário: cadastrar foto do dispositivo
- **Dado** que a pessoa autenticada selecionou uma imagem compatível de até 2 MB
- **Quando** confirma o envio junto aos dados da peça
- **Então** a imagem fica persistida no item da própria conta e aparece no armário após recarregar a página

#### Cenário: usar imagem hospedada em outra loja
- **Dado** que a pessoa informa um link HTTPS direto para uma imagem
- **Quando** salva a peça
- **Então** o armário usa esse link como foto e informa que a loja de origem pode bloquear a exibição externa

#### Cenário: recusar arquivo incompatível
- **Dado** que o arquivo não seja JPG, PNG ou WebP, ou exceda 2 MB
- **Quando** a pessoa tenta carregá-lo
- **Então** o sistema mostra uma mensagem clara e não persiste o arquivo

## Fidelidade

### RF-FID-01 — Pontos vinculados a desafios

Cada desafio válido concede pontos uma única vez por conta. Pontuação e nível são derivados do progresso persistido e não representam crédito financeiro.

#### Cenário: conclusão repetida
- **Dado** que a conta já concluiu um desafio
- **Quando** envia novamente a conclusão
- **Então** o progresso e os pontos permanecem iguais

## Alfaiataria e depoimentos

### RF-SERV-01 — Solicitar ajuste

O sistema deve persistir solicitações de ajuste com descrição da peça, serviço e observações, vinculadas à conta e com estado operacional visível.

### RF-DEP-01 — Publicar relato autorizado

Depoimentos devem ser enviados por usuário autenticado, com autorização explícita, e permanecer ocultos até moderação administrativa.

#### Cenário: relato pendente
- **Dado** que a pessoa envia texto e autoriza sua publicação
- **Quando** a solicitação é registrada
- **Então** ela aparece apenas para a pessoa e para a gestão até aprovação

## Pagamento

### RF-PAG-01 — Checkout Mercado Pago Orders

O checkout de produtos cobrados deve usar o Mercado Pago Checkout Pro Orders com preço recalculado pelo servidor, chave idempotente e reserva de estoque. Sem credenciais, deve informar que o pagamento não está habilitado e não criar pedido pago.

### RF-PAG-02 — Confirmação por webhook

O retorno do navegador não confirma pagamento. Apenas webhook com assinatura válida, consulta autenticada ao Mercado Pago e correspondência de referência/total pode marcar o pedido como pago.

#### Cenário: webhook repetido
- **Dado** que uma Order já foi processada
- **Quando** o Mercado Pago reenvia a mesma notificação
- **Então** o sistema preserva o estado e não duplica efeitos

## Privacidade

### RF-PRI-01 — Transparência e solicitações

A página pública deve explicar os dados tratados conforme modo SQLite/Xano, pagamento, e-mail e recomendações, e oferecer canal persistido para solicitações de titulares.

#### Cenário: pedido de titular
- **Dado** que a pessoa está autenticada
- **Quando** registra uma solicitação de privacidade
- **Então** ela é salva vinculada à conta e não fica pública
