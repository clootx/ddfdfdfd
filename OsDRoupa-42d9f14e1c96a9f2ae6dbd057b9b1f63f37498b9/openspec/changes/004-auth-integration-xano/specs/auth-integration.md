# Spec — Integração de Autenticação com Xano

## Identificador

`004-auth-integration-xano`

## Requisitos Funcionais

### RF-01 — Login Real via Xano

**Endpoint:** `POST https://x8ki-letl-twmt.n7.xano.io/api:nqm5-KuC/auth/login`

**Payload:**
```json
{ "email": "string", "password": "string" }
```

**Resposta de sucesso (200):**
```json
{ "authToken": "jwt...", "user_id": 123 }
```

**Erro (400 / accessdenied):**
```json
{ "message": "Invalid Credentials." }
```

**Comportamento esperado:**
- Pré-validações locais (e-mail formato, senha ≥ 8 chars) executadas antes de enviar
- `is_loading = True` antes da chamada; `False` no `finally`
- Token armazenado em `AuthState.auth_token`
- Redirecionamento para `/dashboard` via `rx.redirect`
- Erro Xano exibido em `AuthState.login_error`

---

### RF-02 — Cadastro Real via Xano (`cadastraCliente`)

**Endpoint:** `POST https://x8ki-letl-twmt.n7.xano.io/api:6LtoY7Zt/cadastraCliente`

**Payload:**
```json
{
  "nome": "string",
  "email": "string",
  "senha": "string",
  "celular": "string",
  "cpf": "",
  "status": "ativo"
}
```

**Resposta de sucesso (200):**
```json
{ "user": {...}, "cliente": {...}, "authToken": "jwt..." }
```

**Erro (400 / accessdenied):**
```json
{ "message": "This account is already in use." }
```

**Comportamento esperado:**
- Pré-validações locais completas (nome, email, senha, confirmação, termos)
- Cria usuário + perfil cliente em um único endpoint
- Token armazenado e redirecionamento para `/dashboard`
- Erro Xano exibido em `AuthState.register_error`

---

### RF-03 — Persistência do Token

- `AuthState.auth_token: str = ""` — armazena o JWT após autenticação
- `AuthState.current_user: dict = {}` — armazena dados do usuário logado
- Disponível para handlers subsequentes (rotas protegidas)

---

### RF-04 — Página Dashboard (stub)

**Rota:** `/dashboard`

**Proteção:** `on_load` verifica `auth_token`. Se vazio → `rx.redirect("/")`

**Conteúdo mínimo:**
- Header com logo e nome do usuário
- Mensagem de boas-vindas
- Botão de logout (limpa token → redireciona para `/`)

---

### RF-05 — Estado de Carregamento

- Botão de login/cadastro exibe indicador ou texto "Aguarde..." enquanto `is_loading == True`
- Botão desabilitado durante o carregamento para evitar dupla submissão

---

## Requisitos Não-Funcionais

- Timeout de 15 segundos nas chamadas HTTP
- Erros de rede (timeout, connection refused) exibem mensagem genérica amigável
- Nenhum dado sensível (senha, token) persistido em localStorage nesta fase
- Handler assíncrono (`async def`) obrigatório para compatibilidade com Reflex e `httpx`
