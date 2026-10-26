# Proposta — 005-dashboard-retirement

## Contexto

A Change 004 criou a rota `/dashboard` como destino inicial após a autenticação. A experiência pública da página inicial já oferece a seção `#como-funciona`, que apresenta a plataforma sem exigir uma tela intermediária de painel. A manutenção do dashboard também deixa a navegação e o fluxo inicial de autenticação mais complexos.

## Objetivo

Remover a página e a rota `/dashboard`, preservando o fluxo de autenticação e encaminhando usuários autenticados para `/#como-funciona`.

## Escopo Incluído

- Remover a interface `dashboard_page` e componentes auxiliares usados exclusivamente por ela.
- Desregistrar a rota `/dashboard` e remover referências de navegação que apontem para ela.
- Usar `/#como-funciona` como destino após login e cadastro bem-sucedidos.
- Preservar a autenticação Xano, o JWT e as demais páginas e rotas existentes.

## Escopo Excluído

- Remover ou alterar a página pública inicial e sua seção “Como funciona”.
- Alterar contratos de API, autenticação, cadastro ou persistência do JWT.
- Remover a página de endereços ou outras funcionalidades protegidas.

## Estado da Implementação

Esta change está proposta para revisão. O redirecionamento após login para `/#como-funciona` já foi aplicado; a exclusão do dashboard do código permanece pendente até a aprovação e execução das tarefas desta change.
