# Proposta: confiabilidade de sessão e recuperação de erros

## Problema

O cliente do OSDROUPA limita chamadas ao Xano, mas ignora o tempo `Retry-After` e algumas falhas temporárias de validação acabam parecendo uma sessão inválida. A tela também oferece “Manter conectado” sem alterar o tipo de cookie e confirma recuperação de senha sem chamar um serviço de e-mail.

## Objetivo

Fazer o app reagir a limites e indisponibilidade do Xano sem deslogar a pessoa, tornar a opção de persistência de sessão real e só confirmar recuperação de senha quando o endpoint de e-mail responder com sucesso.

## Escopo

- Respeitar `Retry-After` em segundos ou data HTTP, manter a fila local e informar o intervalo correto.
- Diferenciar sessão expirada de falha temporária e de acesso negado a um recurso.
- Usar cookie de sessão quando “Manter conectado” estiver desligado e cookie persistente por até 24 horas quando estiver ligado.
- Evitar confirmar uma recuperação que não foi enviada; identificar a configuração de e-mail necessária no Xano.
- Atualizar o contexto técnico que ainda descreve etapas antigas.

## Fora do escopo

- Contornar cotas do Xano ou repetir automaticamente operações que alteram dados.
- Criar ou revelar credenciais de SendGrid, Asaas ou OpenAI.
- Publicar alterações no workspace Xano sem uma prévia suportada e revisão do destino.

## Critérios de aceite

- Um `429` respeita o intervalo retornado pelo servidor e aparece ao usuário como limite temporário.
- Um `429`, `5xx` ou erro de rede durante validação não apaga o token nem redireciona automaticamente ao login.
- Uma resposta `403` de recurso não apaga uma sessão que já foi validada.
- A escolha “Manter conectado” controla se o cookie persiste após fechar o navegador.
- Enquanto o endpoint Xano estiver ligado ao envio de demonstração, a interface informa que a recuperação ainda não está configurada para o e-mail da conta.
