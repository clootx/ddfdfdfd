# Requisitos de confiabilidade e recuperação

## Requisito: respeitar limite temporário do Xano

O cliente deve limitar chamadas locais e respeitar o intervalo indicado pelo Xano após uma resposta `429`, sem repetir automaticamente operações de escrita.

### Cenário: limite com espera em segundos

- **Dado** que uma resposta do Xano contém `429` e `Retry-After: 12`
- **Quando** o cliente agenda a próxima chamada
- **Então** ele aguarda pelo menos 12 segundos e informa essa espera na interface

### Cenário: servidor não informa espera

- **Dado** que o Xano responde `429` sem `Retry-After`
- **Quando** o cliente agenda a próxima chamada
- **Então** ele usa a janela local de 20 segundos e não repete automaticamente a operação que falhou

## Requisito: preservar sessão durante indisponibilidade

Uma falha transitória na validação não deve ser interpretada como credencial inválida.

### Cenário: validação limitada temporariamente

- **Dado** que o token ainda está no navegador e o endpoint `/auth/me` responde `429` ou `5xx`
- **Quando** uma rota protegida valida a conta
- **Então** o token permanece disponível, a rota mostra o erro temporário e oferece nova tentativa

### Cenário: acesso negado a um recurso

- **Dado** que `/auth/me` validou a sessão e um endpoint de recurso responde `403`
- **Quando** o app trata a resposta
- **Então** ele informa o erro de autorização sem apagar a sessão

## Requisito: opção de persistência explícita

O controle “Manter conectado” deve decidir se o cookie dura até o fim da sessão do navegador ou por até 24 horas.

### Cenário: opção desmarcada

- **Dado** que a pessoa entra sem marcar “Manter conectado”
- **Quando** fecha o navegador
- **Então** o token armazenado no cookie de sessão deixa de ser enviado ao reabrir

### Cenário: opção marcada

- **Dado** que a pessoa entra com “Manter conectado” marcado
- **Quando** fecha e reabre o navegador em até 24 horas
- **Então** o cookie persistente restaura a sessão e o Xano valida o token

## Requisito: não confirmar recuperação não enviada

O app não deve afirmar que enviou um link enquanto o endpoint Xano usar a tela e o serviço de e-mail de demonstração.

### Cenário: recuperação ainda não configurada

- **Dado** que o endpoint Xano envia somente ao proprietário da instância e não ao endereço da conta
- **Quando** a pessoa seleciona “Esqueci a senha”
- **Então** a interface informa que a recuperação por e-mail ainda precisa ser configurada no Xano e não chama esse endpoint

### Cenário: SendGrid configurado futuramente

- **Dado** que o Xano enviar o link ao próprio endereço da conta por SendGrid
- **Quando** a recuperação for habilitada em uma change futura
- **Então** a resposta deverá evitar enumeração de e-mails e não afirmar envio quando o provedor falhar
