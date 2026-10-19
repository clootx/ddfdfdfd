# Especificação — Remoção do Dashboard

## RF-DASH-01: Remoção da rota Dashboard

Após a aplicação desta change, o frontend não deve registrar nem renderizar a página `/dashboard`.

### Cenário: Acesso à antiga rota

- **Dado** que a change foi aplicada,
- **Quando** um usuário tenta acessar `/dashboard`,
- **Então** a aplicação não deve exibir a antiga página de painel.

## RF-DASH-02: Destino após autenticação

Após login ou cadastro bem-sucedidos, o frontend deve preservar a sessão autenticada e navegar para `/#como-funciona`.

### Cenário: Login bem-sucedido

- **Dado** que um usuário possui credenciais válidas,
- **Quando** ele conclui o login,
- **Então** o token JWT permanece disponível no estado de autenticação,
- **E** o navegador abre a seção `#como-funciona` da página inicial.

### Cenário: Cadastro bem-sucedido

- **Dado** que um novo usuário informa dados válidos,
- **Quando** o cadastro é concluído com sucesso,
- **Então** o token JWT permanece disponível no estado de autenticação,
- **E** o navegador abre a seção `#como-funciona` da página inicial.

## RF-DASH-03: Navegação sem referências ao Dashboard

A navegação da aplicação não deve conter links para a rota removida `/dashboard`.

### Cenário: Navegar a partir de endereços

- **Dado** que o usuário está na página de endereços,
- **Quando** ele usa a navegação para retornar à área pública,
- **Então** a navegação leva à página inicial,
- **E** não oferece um link para `/dashboard`.

## RF-DASH-04: Preservação das demais rotas

A remoção do dashboard não deve remover nem alterar o fluxo de autenticação Xano, o cadastro, o logout ou as demais páginas da aplicação.

### Cenário: Acessar endereços

- **Dado** que o usuário autenticado abre a página de endereços,
- **Quando** a página termina de carregar,
- **Então** o fluxo de endereços continua disponível sem depender da página Dashboard.
