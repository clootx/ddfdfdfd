# Design: confiabilidade de sessão e recuperação de erros

## Cliente Xano

`XanoAsyncClient` continua limitando este processo a 8 chamadas por janela de 20 segundos. Ao receber `429`, calcula o intervalo a partir de `Retry-After` (número de segundos ou data HTTP), aplica esse intervalo ao cooldown e não repete a requisição automaticamente. Operações de escrita permanecem sem repetição automática.

## Sessão Reflex

`AuthState` passa a distinguir três resultados: sessão válida, login necessário e validação temporariamente indisponível. Só `401` vindo da validação de `/auth/me` limpa os cookies e exige novo login. Erros temporários preservam o token e exibem ação de nova tentativa. Respostas `403` dos recursos permanecem erros de autorização do recurso.

O cookie persistente atual continua com validade máxima de 24 horas. Um segundo cookie sem `max_age` guarda a sessão apenas até o navegador ser encerrado. O evento de login grava o token em apenas um dos dois.

## Redefinição de senha

O endpoint atual de Xano usa o provedor de e-mail de demonstração, que envia somente para o proprietário da instância e aponta para a tela de demonstração do Xano. O frontend não chama esse endpoint e agora informa que a recuperação não está configurada para a conta.

Para habilitar o fluxo completo, o Xano precisa enviar o token de uso único pelo `sendgrid_basic_send` ao próprio endereço da conta, apontar para uma tela de redefinição OSDROUPA e responder sem revelar se o e-mail existe. O ambiente precisa conter `sendgrid_api_key` e `sendgrid_from_email`; essa alteração ainda requer validação e publicação no Xano.

## Persistência e publicação

Não há migração de banco prevista. A alteração XanoScript fica local até ser validada em sandbox ou por uma prévia de importação suportada pelo workspace. Nenhum segredo é versionado.
