# Proposta — 006-persistent-account-profile-wardrobe

## Contexto

O token de autenticação era mantido somente no estado server-side do Reflex. Ao recarregar ou abrir diretamente a home, as páginas não recuperavam nem confirmavam a conta no Xano; somente algumas rotas protegidas verificavam a presença do token, sem validar seu usuário. O sistema também não tem uma área de perfil ou um armário pessoal para a pessoa autenticada.

## Objetivo

Persistir a sessão entre rotas e recarregamentos, validar a conta no Xano em cada entrada de página e entregar áreas de perfil e guarda-roupa digital acessíveis a partir da home.

## Escopo incluído

- Persistir o JWT em cookie de navegador por 24 horas, alinhado à expiração configurada no endpoint de login.
- Consultar `/auth/me` ao entrar nas páginas para confirmar a validade da sessão e carregar os dados atualizados do usuário.
- Carregar o cadastro de cliente por `/buscaCliente` quando o usuário for validado.
- Manter a home pública disponível e exibir atalhos autenticados após validar uma sessão existente.
- Proteger `/enderecos`, `/perfil` e `/armario`; visitantes sem sessão válida são enviados para `/login`.
- Criar `/perfil` com dados de conta e cliente retornados pelo Xano.
- Criar `/armario` com cadastro, remoção, busca e filtros de peças, guardando o acervo no navegador e separando-o por usuário.
- Acrescentar navegação entre home, perfil, armário e endereços.

## Fora do escopo

- Criar tabelas ou publicar endpoints no Xano para roupas pessoais. A API disponível contém o catálogo comercial, sem um contrato de armário por cliente; este MVP guarda as peças no navegador.
- Sincronizar o armário entre dispositivos.
- Editar dados cadastrais do cliente.

## Referências visuais

O perfil usa hierarquia editorial e blocos de conteúdo inspirados em [We Are OSM](https://weareosm.com/). O armário usa cabeçalho de coleção, indicadores e cartões de acesso rápido inspirados em [SquadEasy](https://www.squadeasy.com/en/), traduzidos para a identidade visual têxtil do OSDroupa.

## Dependências

- Autenticação Xano definida em [`openspec/specs/auth/spec.md`](../../../specs/auth/spec.md).
- API atual de perfil de cliente `GET /api:6LtoY7Zt/buscaCliente`.
- Reflex 0.9.12, com estado de sessão e armazenamento de navegador.
