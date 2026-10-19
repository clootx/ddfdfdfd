# Especificação — Sessão Persistente, Perfil e Armário

## RF-006-01: Persistência da sessão
Após login ou cadastro, o JWT deve ficar em cookie disponível em todas as rotas e sobreviver ao recarregamento, respeitando a expiração do token.

## RF-006-02: Validação da conta por rota
Ao abrir ou recarregar uma página, a aplicação consulta `/auth/me` com `Authorization: Bearer <token>`. Usuário, `account_id` e cliente vêm do Xano. A home permanece pública e mostra atalhos autenticados somente após validar a sessão.

## RF-006-03: Proteção de páginas privadas
As rotas `/enderecos`, `/perfil` e `/armario` só mostram conteúdo após validação positiva. Sem token válido, redirecionam para `/login`.

## RF-006-04: Perfil do cliente
`/perfil` mostra nome, e-mail, celular, vínculo de conta e confirmação de sessão validada. Usuário vem de `/auth/me`; cliente vem de `GET /buscaCliente` autenticado pelo Bearer e associado pelo `$auth.id`.

## RF-006-05: Armário digital
`/armario` permite adicionar/remover peças, pesquisar e filtrar por categoria. O cache local é separado pelo ID do usuário. A sincronização Xano é especificada na change 009.

## RF-006-06: Proteção do token
O JWT trafega somente no cabeçalho `Authorization: Bearer <token>`, nunca em URL ou query string.

## RF-006-07: Integridade do cadastro
O formulário não cria CPF a partir do celular ou de valores aleatórios/temporais. CPF só pode ser persistido quando fornecido explicitamente por um fluxo que o coleta.

## Cenários de aceitação

### Login seguido de recarregamento da home
- **Dado** que o Xano autenticou o usuário e retornou um JWT
- **Quando** a pessoa abre ou recarrega `/`
- **Então** o cookie restaura o JWT, `/auth/me` valida a conta e a home exibe os atalhos autenticados

### Sessão expirada
- **Dado** que o cookie contém um JWT rejeitado pelo Xano
- **Quando** a pessoa abre `/perfil` ou `/armario`
- **Então** a aplicação apaga a sessão local e redireciona para `/login`

### Perfil autenticado
- **Dado** que `/auth/me` confirmou a sessão
- **Quando** a pessoa acessa `/perfil`
- **Então** vê usuário e cliente atualizados, sem enviar o JWT em query string

### Separação de acervos
- **Dado** que uma conta possui peças salvas no navegador
- **Quando** outra conta é validada no mesmo navegador
- **Então** as peças da conta anterior não são exibidas

### Cadastro sem CPF
- **Dado** que o formulário não coleta CPF
- **Quando** a conta é criada
- **Então** celular não é copiado para CPF e nenhum CPF artificial é gravado