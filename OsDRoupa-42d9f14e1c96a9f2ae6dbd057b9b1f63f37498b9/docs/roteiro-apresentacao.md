# Roteiro de apresentação — OSDROUPA

## Antes de apresentar

1. Abra a versão preparada em `http://localhost:3011/`. Se o servidor tiver sido encerrado, inicie o projeto na pasta raiz:

   ```powershell
   .\.venv\Scripts\python.exe -m reflex run --env prod --single-port --frontend-port 3011
   ```

2. Crie uma conta de demonstração em `/cadastro` ou deixe uma conta de teste pronta. O cadastro pede nome completo, e-mail, celular, aceite dos termos e senha com pelo menos oito caracteres, uma letra maiúscula, um número e um símbolo.
3. Separe uma foto JPG, PNG ou WebP de até 2 MB. Como alternativa, copie o link HTTPS direto do arquivo de imagem. Um link de página de produto pode não funcionar como imagem.
4. Deixe uma conta de demonstração com endereço pronto. Para mostrar a loja sem credenciais Mercado Pago, use só os produtos demonstrativos; esse pedido não cobra.

## Fluxo recomendado — 7 a 9 minutos

### 1. Apresente a proposta na página inicial

Abra `/` e explique que o OSDROUPA conecta loja, armário digital e serviços de alfaiataria para ajudar a pessoa a aproveitar melhor as próprias roupas.

### 2. Mostre a entrada e o retorno à página inicial

Entre em `/cadastro`, crie a conta de demonstração e mostre o retorno para `/#como-funciona`. Se a conta já existir, use `/login`.

### 3. Personalize o perfil

Em `/perfil`, atualize nome, celular e preferências opcionais de estilo, cores e tamanhos. Mostre que o e-mail de login não é editado por esse formulário.

### 4. Cadastre uma peça no armário

Abra `/armario`, escolha **Adicionar peça**, preencha nome, categoria e estado de uso. Envie a foto preparada ou informe o link direto da imagem, confira a prévia e salve. Explique que o modo SQLite salva a foto com a peça e a associa à conta.

### 5. Gere e planeje uma combinação

Em `/look-do-dia`, escolha clima e ocasião para receber sugestões baseadas nas peças cadastradas. Salve a combinação e mostre-a em `/looks` ou organize uma data em `/calendario`.

### 6. Conecte desafios e fidelidade

Abra `/desafios`, filtre por tema ou andamento e acesse uma atividade relacionada. Marque como concluída somente se a ação foi feita. Em seguida, acesse `/fidelidade` para mostrar nível, avanço e histórico. Explique que os pontos representam progresso e não são dinheiro ou saldo resgatável.

### 7. Mostre o serviço de alfaiataria

Apresente `/servicos` e abra `/servicos/solicitar` para demonstrar o formulário de pedido de ajuste. O envio registra uma solicitação; não confirma orçamento nem agendamento.

### 8. Feche com loja, pagamento e privacidade

No `/loja`, salve um produto nos favoritos, filtre a coleção e abra a sacola. No checkout, revise os itens e o subtotal estimado. Sem credenciais, demonstre o pedido sem cobrança; com Mercado Pago sandbox configurado, mostre apenas o redirecionamento e a confirmação pendente por webhook. Termine em `/privacidade`.

## O que afirmar com precisão

- O armário aceita foto enviada no backend SQLite local ou link HTTPS direto para uma imagem.
- O perfil guarda preferências opcionais na conta; favoritos são separados por usuário no navegador.
- As sugestões de looks usam o acervo cadastrado e as escolhas da pessoa; não geram imagens de roupas por IA.
- O checkout demonstrativo registra um pedido sem cobrança. O subtotal mostrado antes do envio é estimado e o servidor recalcula o valor.
- O pagamento real usa o checkout hospedado Mercado Pago quando configurado. O app não coleta cartão e aguarda confirmação do webhook; a disponibilidade de Pix ou cartão depende da conta vendedora.
- A recuperação por e-mail requer SMTP. O modo SQLite é local e voltado ao desenvolvimento/demonstração.

## Checagens realizadas para este roteiro

- O Reflex compilou com sucesso em modo `--dry`.
- A versão atual respondeu com HTTP 200 na home e nas rotas de cadastro, login, armário, looks, calendário, desafios, fidelidade, serviços, depoimentos, privacidade, loja e checkout.
- Em uma base temporária isolada, cadastro, login, upload de imagem e separação de peças entre duas contas foram confirmados. Essa verificação não alterou a base de dados real.
- A interação visual dos formulários no navegador e o pagamento Mercado Pago real não foram validados nesta checagem.
