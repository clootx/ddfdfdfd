# Especificação Consolidada — Autenticação e Sessão (Auth)

> **Origem:** Promovida a partir de [`001-foundation-identity-client`](../../changes/archive/001-foundation-identity-client/) e consolidada com as changes [`004-auth-integration-xano`](../../changes/004-auth-integration-xano/) e [`006-persistent-account-profile-wardrobe`](../../changes/006-persistent-account-profile-wardrobe/).

## 1. Visão Geral
Define as capacidades de autenticação, emissão e validação de tokens JWT de sessão, recuperação de perfil do usuário, e proteção de rotas no ecossistema OSDroupa integrado ao backend Xano e frontend Reflex.

## 2. Endpoints e Contratos Canônicos

| Operação | Endpoint Xano | Método | Cabeçalhos | Payload de Entrada | Resposta Sucesso |
|---|---|---|---|---|---|
| **Login** | `/api:nqm5-KuC/auth/login` | POST | `Content-Type: application/json` | `{"email", "password"}` | `{"authToken": "jwt...", "user_id": int}` |
| **Cadastro** | `/api:6LtoY7Zt/cadastraCliente` | POST | `Content-Type: application/json` | `{"nome", "email", "senha", "celular", "status"}` (`cpf` opcional quando coletado) | `{"user": {...}, "cliente": {...}, "authToken": "jwt..."}` |
| **Sessão / Perfil** | `/api:nqm5-KuC/auth/me` | GET | `Authorization: Bearer <token>` | Nenhum | `{"id", "name", "email", "account_id", "role"}` |
| **Cadastro de cliente** | `/api:6LtoY7Zt/buscaCliente` | GET | `Authorization: Bearer <token>` | Nenhum | Registro `CLIENTE` da conta autenticada |

## 3. Requisitos Funcionais

### RF-AUTH-01: Cadastro Integrado de Usuário e Cliente
O sistema deve permitir a criação de novos usuários e perfil cliente em uma única transação no Xano:
- Validação prévia de formato de e-mail e força de senha no frontend Reflex.
- Hashing de senha e criação do registro em `user` e `CLIENTE` no Xano.
- Tratamento de unicidade de e-mail e de CPF quando CPF for fornecido explicitamente.
- Retorno automático de `authToken` JWT e dados do perfil.

### RF-AUTH-02: Autenticação Real com Xano (Login)
O sistema deve validar as credenciais fornecidas contra o endpoint `/auth/login` do Xano:
- Quando válidas, emite o `authToken` JWT e enriquece os dados do usuário via `/auth/me`.
- Quando inválidas, retorna mensagem amigável ("Invalid Credentials.") sem expor dados internos.

### RF-AUTH-03: Sessão Segura e Contexto do Usuário
O endpoint `/auth/me` deve validar o token passado no cabeçalho `Authorization: Bearer <token>` e retornar a identificação do usuário e seu vínculo com a conta (`account_id`).

### RF-AUTH-04: Persistência da Sessão entre Rotas
- O `authToken` é mantido em cookie de navegador por até 24 horas e disponibilizado em `AuthState.auth_token` em todas as rotas.
- Os dados do usuário logado ficam disponíveis de forma reativa em `AuthState.current_user`, `AuthState.user_display_name` e `AuthState.user_email`.
- O usuário e o cliente devem ser novamente obtidos do Xano ao carregar cada rota.

### RF-AUTH-05: Proteção de Rotas
- Rotas privadas (`/enderecos`, `/perfil` e `/armario`) devem validar o JWT em `/auth/me` no evento `on_load` antes de exibir seu conteúdo.
- Usuários sem token ou com sessão inválida que tentarem acessar rotas privadas são redirecionados para `/login`.
- A home `/` permanece pública, restaura sessões existentes e apresenta atalhos autenticados após a validação do usuário.
- As páginas públicas `/loja`, `/produto` e `/carrinho` também restauram sessões existentes e apresentam atalhos autenticados após a validação do usuário.
- Usuários autenticados no login ou cadastro são redirecionados automaticamente para a seção `#como-funciona` da página inicial.

- Rotas publicas `/inspiracao`, `/artigos` e `/artigo` restauram a sessao existente no `on_load`.

### RF-AUTH-06: Perfil e Armário Pessoal
- A rota `/perfil` apresenta os dados de usuário de `/auth/me` e os dados do cliente de `/buscaCliente`.
- A rota `/armario` permite cadastrar, remover, pesquisar e filtrar peças do acervo pessoal.
- O armário usa o backend configurado (SQLite local ou Xano) como fonte de verdade e mantém cache separado por conta. No SQLite, fotos enviadas são armazenadas como dados privados da peça; no Xano, o formulário aceita links HTTPS diretos.

### RF-AUTH-07: Logout Seguro
- A ação `AuthState.logout` deve limpar `auth_token`, `current_user` e campos de formulário, redirecionando para a página de entrada `/`.

### RF-AUTH-08: Integridade do cadastro e do token
- O cadastro não usa celular como CPF nem fabrica um CPF.
- O JWT trafega somente no cabeçalho `Authorization: Bearer <token>`, nunca na URL.
## 4. Cenários de Aceitação Consolidados

### Cenário: Autenticação bem-sucedida e redirecionamento
- **Dado** que um usuário está cadastrado no Xano,
- **Quando** ele envia suas credenciais corretas via formulário de login,
- **Então** o sistema armazena o `authToken` no estado e o redireciona para `/#como-funciona`.

### Cenário: Credenciais inválidas
- **Dado** uma tentativa de login com senha incorreta ou e-mail inexistente,
- **Quando** a requisição de login é processada pelo Xano,
- **Então** o sistema exibe o erro "Credenciais inválidas. Tente novamente." inline no formulário e não redireciona.

### Cenário: Cadastro bem-sucedido de cliente
- **Dado** que um novo usuário preenche os campos obrigatórios de cadastro e aceita os termos,
- **Quando** ele clica em "Criar conta",
- **Então** o backend Xano cria o usuário, cria o registro do cliente, retorna o JWT e o frontend redireciona para `/#como-funciona`.

### Cenário: Acesso não autorizado a rota protegida
- **Dado** um visitante sem token de autenticação,
- **Quando** ele tenta acessar diretamente a URL `/perfil`,
- **Então** o guard valida que não há sessão e redireciona para `/login`.

### Cenário: Logout
- **Dado** um usuário logado na página `/perfil`,
- **Quando** ele clica no botão "Sair",
- **Então** a sessão é encerrada, o token é removido e o usuário retorna para `/`.

### Cenário: Conta lembrada ao recarregar a home
- **Dado** que a pessoa entrou e o cookie ainda contém um JWT válido,
- **Quando** ela recarrega `/`,
- **Então** a aplicação confirma o token em `/auth/me` e exibe os atalhos de perfil e armário.

### Cenário: Acesso a perfil ou armário sem sessão válida
- **Dado** que a pessoa não tem um JWT válido,
- **Quando** acessa `/perfil` ou `/armario`,
- **Então** o conteúdo privado não é exibido e a pessoa é redirecionada para `/login`.

### Cenário: Dados do perfil e armário pessoal
- **Dado** que a sessão foi validada no Xano,
- **Quando** a pessoa abre `/perfil` ou `/armario`,
- **Então** o perfil mostra os dados atualizados do usuário e cliente, e o armário mostra as peças do Xano ou o cache local daquela conta quando a sincronização estiver indisponível.

### Cenario: Perfil sem JWT na URL
- **Dado** que a aplicacao solicita os dados do cliente autenticado
- **Quando** consulta `/buscaCliente`
- **Entao** envia o token somente no cabecalho Bearer e o Xano deriva o cliente do usuario autenticado

### Cenario: Cadastro sem CPF coletado
- **Dado** que o formulario de cadastro nao solicita CPF
- **Quando** cria uma conta
- **Entao** o sistema nao usa o celular como CPF nem inventa um valor
