# Design Técnico — Integração de Autenticação com Xano

## Arquitetura da Solução

```
AuthState (Reflex)
    │
    ├── handle_login() ──async──► POST /api:nqm5-KuC/auth/login
    │                                   │
    │                             sucesso: authToken → state
    │                                   │── rx.redirect("/dashboard")
    │                             erro:   login_error ← message
    │
    └── handle_register() ──async──► POST /api:6LtoY7Zt/cadastraCliente
                                          │
                                    sucesso: authToken → state
                                          │── rx.redirect("/dashboard")
                                    erro:   register_error ← message
```

## Constantes

```python
XANO_BASE = "https://x8ki-letl-twmt.n7.xano.io"
XANO_AUTH  = f"{XANO_BASE}/api:nqm5-KuC/auth"
XANO_PDB   = f"{XANO_BASE}/api:6LtoY7Zt"
XANO_TIMEOUT = 15.0  # segundos
```

## Novos Campos no AuthState

```python
auth_token: str = ""
current_user: dict = {}
```

## Handler de Login (async)

```python
async def handle_login(self):
    # 1. Validações locais (e-mail, senha)
    # 2. self.is_loading = True
    # 3. async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
    #        resp = await client.post(f"{XANO_AUTH}/login", json={...})
    # 4. if resp.status_code == 200:
    #        data = resp.json()
    #        self.auth_token = data["authToken"]
    #        return rx.redirect("/dashboard")
    # 5. else: self.login_error = resp.json().get("message", "Erro ao autenticar.")
    # 6. finally: self.is_loading = False
```

## Handler de Cadastro (async)

```python
async def handle_register(self):
    # 1. Validações locais completas
    # 2. self.is_loading = True
    # 3. async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
    #        resp = await client.post(f"{XANO_PDB}/cadastraCliente", json={...})
    # 4. if resp.status_code == 200:
    #        data = resp.json()
    #        self.auth_token = data["authToken"]
    #        return rx.redirect("/dashboard")
    # 5. else: self.register_error = resp.json().get("message", "Erro no cadastro.")
    # 6. finally: self.is_loading = False
```

## Guard de Rota (Dashboard)

```python
class DashboardState(rx.State):
    async def check_auth(self):
        if not AuthState.auth_token:
            return rx.redirect("/")
```

> **Nota:** Como o `auth_token` está no `AuthState` (estado pai), o `DashboardState` pode acessá-lo via `self.auth_token` se herdar de `AuthState`, ou via substato compartilhado. Optaremos por consolidar tudo no `AuthState` para simplicidade desta fase.

## Tratamento de Erros de Rede

```python
except httpx.TimeoutException:
    self.login_error = "Servidor demorou para responder. Tente novamente."
except httpx.RequestError:
    self.login_error = "Erro de conexão. Verifique sua internet."
```

## Página Dashboard (stub)

Componente mínimo com:
- Header: logo + nome do usuário (`AuthState.current_user.get("name", "Usuário")`)
- Card de boas-vindas
- Botão de logout: limpa `auth_token` → `rx.redirect("/")`

## Impacto em Arquivos

| Arquivo | Tipo de Mudança |
|---|---|
| `OSDroupa/OSDroupa.py` | Edição: + import httpx, + constantes, + campos state, ~ handlers, + dashboard_page |
| `openspec/changes/README.md` | Edição: adicionar entrada da Change 004 |
