# Design Técnico — 002-auth-landing-page

## Arquitetura de Interface e Tokens de Design

A identidade visual do **OSDroupa** inspira-se na alfaiataria, no denim e na tecnologia conectada.

### Tokens de Cores e Tipografia
- `INK`: `#0F1A33` — Azul meia-noite profundo (fundos escuros, textos primários).
- `DENIM`: `#1F3560` — Tom índigo estrutural (gradientes e estados hover).
- `CHALK`: `#F3F1EC` / `#F8F9FA` — Algodão cru suave para o painel de formulários.
- `THREAD`: `#E9A23B` — Ocre/Dourado pesponto têxtil (focos, destaques e animações).
- `MUTED`: `#5F6B85` — Cinza ardósia para rótulos secundários e legendas.
- `ERROR`: `#B4372F` — Vermelho tijolo para alertas de validação.
- `OK`: `#2F7A4F` — Verde folha para sucesso.

### Tipografia
- `DISPLAY`: `'Bricolage Grotesque', sans-serif` (Títulos e logotipo).
- `BODY`: `'Figtree', sans-serif` (Textos corridos e formulários).

## Estrutura de Componentes no Reflex

```text
auth_shell(mode: "login" | "register")
│
├── brand_panel()
│   ├── Logo e nome da marca (OSDROUPA)
│   ├── Heading expressivo ("Abra o armário já sabendo o que vestir.")
│   ├── Subtítulo e proposta de valor
│   ├── Card da Arara SVG animada (peças em cabides + tag 22°C Reunião)
│   └── Badges dos 3 pilares (IA Looks, Arara RFID/LEDs, Sustentabilidade)
│
└── form_panel(is_login: bool)
    ├── mode_tabs(is_login) — Alternador "Entrar" | "Criar conta"
    ├── Cabeçalho contextual (Título + Subtítulo acolhedor)
    ├── Formulário Ativo:
    │   ├── login_form() (E-mail, Senha com olho, Lembrar-me, Esqueci senha, Botão Entrar)
    │   └── register_form() (Nome, E-mail, Celular, Senha, Strength Meter, Confirmação, Termos)
    ├── Feedback visual (Alertas de erro e status de sucesso)
    └── Rodapé de suporte e segurança
```

## Modelo de Estado (`AuthState`)

```python
class AuthState(rx.State):
    # Campos de Login
    login_email: str = ""
    login_password: str = ""
    remember_me: bool = False
    
    # Campos de Cadastro
    full_name: str = ""
    register_email: str = ""
    phone: str = ""
    register_password: str = ""
    confirm_password: str = ""
    accepted_terms: bool = False
    
    # Estados de Controle da Interface
    show_password: bool = False
    is_loading: bool = False
    login_error: str = ""
    login_success: str = ""
    register_error: str = ""
    register_success: str = ""
    forgot_password_msg: str = ""
```

## Manipuladores de Eventos (Event Handlers)

1. `toggle_password()`: Inverte a flag `show_password` para alternar os inputs entre `text` e `password`.
2. `handle_login()`: Valida formato do e-mail e tamanho da senha, ativa `is_loading` e processa a autenticação.
3. `handle_register()`: Valida nome e sobrenome, e-mail, celular, requisitos da senha, confirmação de senha idêntica e aceite dos termos.
4. `handle_forgot_password()`: Aciona feedback amigável informando envio de link de redefinição para o e-mail digitado.
