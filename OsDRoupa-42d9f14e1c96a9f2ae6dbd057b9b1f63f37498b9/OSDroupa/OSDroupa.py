import json
import re
import unicodedata
import uuid
import typing
from decimal import Decimal, InvalidOperation
import httpx
import reflex as rx
from rxconfig import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ── Xano API ────────────────────────────────────────────────────────────────
XANO_BASE    = "https://x8ki-letl-twmt.n7.xano.io"
XANO_AUTH    = f"{XANO_BASE}/api:nqm5-KuC/auth"
XANO_PDB     = f"{XANO_BASE}/api:6LtoY7Zt"
XANO_DB      = f"{XANO_BASE}/api:EzKvuCov"
XANO_TIMEOUT = 15.0  # segundos
HOME_AFTER_AUTH = "/#como-funciona"
STORE_CATEGORIES = ("Roupas", "Calçados", "Acessórios")

# ── Tokens de Design & Alfaiataria Tecnológica ────────────────────────────
INK = "#0F1A33"          # Azul meia-noite profundo
DENIM = "#1F3560"        # Índigo clássico
CHALK = "#F8F9FA"        # Algodão cru limpo e acolhedor
THREAD = "#E9A23B"       # Ocre dourado pesponto têxtil
MUTED = "#5F6B85"        # Ardósia suave para textos secundários
MUTED_BG = "rgba(15,26,51,0.05)"
ERROR = "#B4372F"        # Vermelho tijolo
OK = "#2F7A4F"           # Verde folha

DISPLAY = "'Bricolage Grotesque', sans-serif"
BODY = "'Figtree', sans-serif"

FONTS = "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700&family=Figtree:wght@400;500;600;700&display=swap"

CSS = f"""
a:focus-visible, button:focus-visible, input:focus-visible {{
    outline: 2px solid {THREAD};
    outline-offset: 3px;
}}
.osd-swing {{
    transform-box: fill-box;
    transform-origin: 190px 30px;
    animation: osd-swing 2.8s ease-in-out 0.4s 1 both;
}}
@keyframes osd-swing {{
    0% {{ transform: rotate(0deg); }}
    20% {{ transform: rotate(5deg); }}
    45% {{ transform: rotate(-3deg); }}
    70% {{ transform: rotate(1.5deg); }}
    100% {{ transform: rotate(0deg); }}
}}
@keyframes marquee {{
    0% {{ transform: translateX(0%); }}
    100% {{ transform: translateX(-50%); }}
}}
.osd-marquee {{
    display: flex;
    width: 200%;
    animation: marquee 26s linear infinite;
}}
.osd-marquee:hover {{
    animation-play-state: paused;
}}
@media (prefers-reduced-motion: reduce) {{
    .osd-swing {{ animation: none; }}
    .osd-marquee {{ animation: none; }}
}}
"""

# ── Ilustração da Arara de Roupas & Look do Dia (SVG) ────────────────────
def _garment(x: int, d: str, fill: str, extra: str = "") -> str:
    return (
        f'<g transform="translate({x} 0)">'
        f'<path d="M0 74 V54 c0-6 8-8 8-16 a8 8 0 0 0 -16 0" fill="none" stroke="#C9D3E8" stroke-width="2" stroke-linecap="round"/>'
        f'<path d="M-36 96 L0 74 L36 96" fill="none" stroke="#C9D3E8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="{d}" fill="{fill}" stroke="rgba(255,255,255,.2)" stroke-width="1.2"/>{extra}</g>'
    )

def _seam(d: str) -> str:
    return f'<path d="{d}" stroke="{THREAD}" stroke-width="1.5" stroke-dasharray="4 4" fill="none"/>'

_TAG = (
    f'<path d="M190 116 L229 177" stroke="{THREAD}" stroke-width="1.5" fill="none"/>'
    f'<g transform="translate(196 168)"><rect width="70" height="58" rx="8" fill="{THREAD}"/>'
    f'<circle cx="35" cy="10" r="3" fill="{INK}"/>'
    f'<text x="35" y="34" text-anchor="middle" font-family="Bricolage Grotesque, sans-serif" font-weight="700" font-size="16" fill="{INK}">22°C</text>'
    f'<text x="35" y="49" text-anchor="middle" font-family="Figtree, sans-serif" font-size="10" font-weight="600" fill="{INK}">Reunião</text></g>'
)

RAIL_SVG = (
    '<svg viewBox="0 0 600 380" style="width:100%;height:auto" role="img" '
    'aria-label="Arara de roupas inteligente com sugestão de look selecionado para 22°C em reunião">'
    f'<line x1="20" y1="30" x2="580" y2="30" stroke="#C9D3E8" stroke-width="3" stroke-linecap="round"/>'
    f'<circle cx="20" cy="30" r="5" fill="#C9D3E8"/><circle cx="580" cy="30" r="5" fill="#C9D3E8"/>'
    + _garment(76, "M-36 96 L0 116 L36 96 L54 124 L48 250 H-48 L-54 124 Z", "#2F4B80", _seam("M0 116 V245"))
    + '<g class="osd-swing">'
    + _garment(190, "M-36 96 L0 116 L36 96 L52 122 L46 205 H-46 L-52 122 Z", "#EDE9DF", _seam("M-14 100 L0 116 L14 100"))
    + _TAG
    + "</g>"
    + _garment(300, "M-34 96 H34 L38 310 H8 L0 170 L-8 310 H-38 Z", "#1B2C52")
    + _garment(410, "M-34 96 L0 112 L34 96 L40 160 L64 300 H-64 L-40 160 Z", "#7C93C2")
    + _garment(524, "M-36 96 L0 116 L36 96 L56 124 L56 330 H-56 L-56 124 Z", "#3A4260", _seam("M0 116 V325"))
    + "</svg>"
)

LOGO_SVG = (
    '<svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">'
    '<path d="M16 13 V10 a3.2 3.2 0 1 0 -3.2 -3.2" fill="none" stroke="#F8F9FA" stroke-width="2.2" stroke-linecap="round"/>'
    '<path d="M16 13 L3.5 23.5 a2 2 0 0 0 1.3 3.5 H27.2 a2 2 0 0 0 1.3 -3.5 Z" fill="none" stroke="#F8F9FA" stroke-width="2.2" stroke-linejoin="round"/>'
    f'<path d="M7 24 H25" stroke="{THREAD}" stroke-width="1.8" stroke-dasharray="2.5 2.5"/></svg>'
)


# ── Gerenciamento de Estado da Autenticação (AuthState) ───────────────────
class AuthState(rx.State):
    # Controle de Aba
    active_tab: str = "login"

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

    # Controles Visuais
    show_password: bool = False
    is_loading: bool = False
    login_error: str = ""
    login_success: str = ""
    register_error: str = ""
    register_success: str = ""
    forgot_password_msg: str = ""

    # Autenticação
    auth_token: str = rx.Cookie(
        "",
        name="osd_auth_token",
        path="/",
        max_age=86400,
        secure=True,
        same_site="lax",
    )
    current_user: dict = {}
    client_profile: dict = {}
    wardrobe_items: list[dict[str, str]] = []
    wardrobe_storage: str = rx.LocalStorage("{}", name="osd_wardrobe_by_account")
    wardrobe_owner_id: str = ""
    account_validated: bool = False
    session_loading: bool = False
    session_error: str = ""

    def set_active_tab(self, tab: str):
        self.active_tab = tab
        self.login_error = ""
        self.register_error = ""
        self.forgot_password_msg = ""

    def set_login_email(self, value: str):
        self.login_email = value
        self.login_error = ""

    def set_login_password(self, value: str):
        self.login_password = value
        self.login_error = ""

    def set_remember_me(self, value: bool):
        self.remember_me = value

    def set_full_name(self, value: str):
        self.full_name = value
        self.register_error = ""

    def set_register_email(self, value: str):
        self.register_email = value
        self.register_error = ""

    def set_phone(self, value: str):
        self.phone = value
        self.register_error = ""

    def set_register_password(self, value: str):
        self.register_password = value
        self.register_error = ""

    def set_confirm_password(self, value: str):
        self.confirm_password = value
        self.register_error = ""

    def set_accepted_terms(self, value: bool):
        self.accepted_terms = value
        self.register_error = ""

    def toggle_password(self):
        self.show_password = not self.show_password

    @rx.var
    def strength(self) -> int:
        p = self.register_password
        if not p:
            return 0
        return sum([
            len(p) >= 8,
            any(c.isupper() for c in p),
            any(c.isdigit() for c in p),
            any(not c.isalnum() for c in p),
        ])

    @rx.var
    def strength_label(self) -> str:
        labels = ["Digite uma senha", "Fraca (mín. 8 caracteres)", "Razoável (adicione números)", "Boa (adicione símbolos)", "Forte e segura"]
        return labels[self.strength]

    @rx.var
    def user_display_name(self) -> str:
        name = self.client_profile.get("nome") or self.current_user.get("name")
        if name:
            return str(name)
        email = self.current_user.get("email")
        if email:
            return str(email).split("@")[0].capitalize()
        return "Usuário"

    @rx.var
    def user_email(self) -> str:
        if not self.current_user:
            return ""
        return str(self.current_user.get("email", ""))

    @rx.var
    def is_authenticated(self) -> bool:
        return bool(self.auth_token and self.account_validated)

    @rx.var
    def profile_phone(self) -> str:
        return str(self.client_profile.get("celular") or "Não informado")

    @rx.var
    def account_id_label(self) -> str:
        account_id = self.current_user.get("account_id")
        return str(account_id) if account_id else "Sem conta vinculada"

    async def _sync_session(self, token: str) -> bool:
        """Valida o JWT no Xano e atualiza usuário e perfil do cliente."""
        self.account_validated = False
        self.session_loading = True
        self.session_error = ""
        self.current_user = {}
        self.client_profile = {}
        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                user_resp = await client.get(f"{XANO_AUTH}/me", headers=headers)
                if user_resp.status_code in (401, 403):
                    self.auth_token = ""
                    self.current_user = {}
                    self.client_profile = {}
                    self.session_error = "Sua sessão expirou. Entre novamente."
                    return False
                if user_resp.status_code != 200:
                    self.session_error = "Não foi possível validar sua conta agora."
                    return False

                user_data = user_resp.json()
                if not isinstance(user_data, dict) or not user_data.get("id"):
                    self.auth_token = ""
                    self.current_user = {}
                    self.client_profile = {}
                    self.session_error = "A conta não foi reconhecida. Entre novamente."
                    return False

                self.current_user = user_data
                self.account_validated = True

                try:
                    client_resp = await client.get(
                        f"{XANO_PDB}/buscaCliente",
                        headers=headers,
                    )
                    if client_resp.status_code == 200:
                        profile_data = client_resp.json()
                        self.client_profile = profile_data if isinstance(profile_data, dict) else {}
                    else:
                        self.client_profile = {}
                except httpx.RequestError:
                    self.client_profile = {}

                return True
        except httpx.TimeoutException:
            self.session_error = "O servidor demorou para validar sua conta."
        except httpx.RequestError:
            self.session_error = "Não foi possível conectar ao servidor de autenticação."
        finally:
            self.session_loading = False

        return False

    async def restore_session(self):
        """Restaura e valida a sessão nas rotas públicas e privadas."""
        if not self.auth_token:
            self.account_validated = False
            self.current_user = {}
            self.client_profile = {}
            self.session_error = ""
            return
        await self._sync_session(str(self.auth_token))

    async def require_authenticated(self):
        """Valida a conta no Xano e impede acesso a páginas privadas sem sessão."""
        if not self.auth_token:
            self.account_validated = False
            self.current_user = {}
            self.client_profile = {}
            return rx.redirect("/login")
        if not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")

    def validate_email(self, value: str) -> bool:
        return bool(EMAIL_RE.match(value.strip()))

    def handle_forgot_password(self):
        if not self.login_email.strip() or not self.validate_email(self.login_email):
            self.forgot_password_msg = "Informe seu e-mail cadastrado acima para receber as instruções de recuperação."
            return
        self.forgot_password_msg = f"Enviamos um link de redefinição para {self.login_email}. Verifique sua caixa de entrada."

    async def handle_login(self):
        self.login_error = ""
        self.login_success = ""
        self.forgot_password_msg = ""

        # Pré-validações locais (evita request desnecessário)
        if not self.login_email.strip():
            self.login_error = "Informe seu e-mail para continuar."
            return
        if not self.validate_email(self.login_email):
            self.login_error = "Digite um e-mail válido (ex.: seu.nome@email.com)."
            return
        if len(self.login_password) < 8:
            self.login_error = "A senha deve conter no mínimo 8 caracteres."
            return

        self.is_loading = True
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                resp = await client.post(
                    f"{XANO_AUTH}/login",
                    json={"email": self.login_email.strip(), "password": self.login_password},
                )
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("authToken", "")
                if not token:
                    self.login_error = "O servidor não retornou uma sessão válida."
                    return
                self.auth_token = token
                if not await self._sync_session(token):
                    self.auth_token = ""
                    self.login_error = self.session_error or "Não foi possível validar sua conta."
                    return
                return rx.redirect(HOME_AFTER_AUTH)
            else:
                payload = resp.json()
                self.login_error = payload.get("message", "Credenciais inválidas. Tente novamente.")
        except httpx.TimeoutException:
            self.login_error = "O servidor demorou para responder. Tente novamente."
        except httpx.RequestError:
            self.login_error = "Erro de conexão. Verifique sua internet e tente novamente."
        finally:
            self.is_loading = False

    async def handle_register(self):
        self.register_error = ""
        self.register_success = ""

        # Pré-validações locais
        if not self.full_name.strip():
            self.register_error = "Informe seu nome completo."
            return
        if len(self.full_name.strip().split()) < 2:
            self.register_error = "Informe pelo menos nome e sobrenome."
            return
        if not self.register_email.strip():
            self.register_error = "Informe seu e-mail para cadastro."
            return
        if not self.validate_email(self.register_email):
            self.register_error = "Digite um endereço de e-mail válido."
            return
        if not self.phone.strip():
            self.register_error = "Informe um celular para contato."
            return
        if len(self.register_password) < 8:
            self.register_error = "A senha precisa ter pelo menos 8 caracteres."
            return
        if not any(c.isupper() for c in self.register_password):
            self.register_error = "A senha deve conter ao menos uma letra maiúscula."
            return
        if not any(c.isdigit() for c in self.register_password):
            self.register_error = "A senha deve conter ao menos um número."
            return
        if not any(not c.isalnum() for c in self.register_password):
            self.register_error = "A senha deve conter ao menos um caractere especial."
            return
        if self.register_password != self.confirm_password:
            self.register_error = "As senhas não conferem. Verifique a digitação."
            return
        if not self.accepted_terms:
            self.register_error = "É necessário aceitar os termos de serviço e privacidade."
            return

        self.is_loading = True
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                resp = await client.post(
                    f"{XANO_PDB}/cadastraCliente",
                    json={
                        "nome": self.full_name.strip(),
                        "email": self.register_email.strip(),
                        "senha": self.register_password,
                        "celular": self.phone.strip(),
                        "status": "ativo",
                    },
                )
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("authToken")
                if not token:
                    user_data = data.get("user", {})
                    msg = user_data.get("message") if isinstance(user_data, dict) else None
                    self.register_error = msg or "Este e-mail já está cadastrado ou dados inválidos."
                    return
                self.auth_token = token
                if not await self._sync_session(token):
                    self.auth_token = ""
                    self.register_error = self.session_error or "Não foi possível validar sua conta."
                    return
                return rx.redirect(HOME_AFTER_AUTH)
            else:
                payload = resp.json()
                self.register_error = payload.get("message", "Erro ao criar conta. Tente novamente.")
        except httpx.TimeoutException:
            self.register_error = "O servidor demorou para responder. Tente novamente."
        except httpx.RequestError:
            self.register_error = "Erro de conexão. Verifique sua internet e tente novamente."
        finally:
            self.is_loading = False

    def logout(self):
        """Encerra a sessão do usuário e redireciona para a página inicial."""
        self.auth_token = ""
        self.current_user = {}
        self.client_profile = {}
        self.account_validated = False
        self.session_error = ""
        self.login_email = ""
        self.login_password = ""
        return rx.redirect("/")

WARDROBE_CATEGORIES = ["Partes de cima", "Partes de baixo", "Vestidos", "Calçados", "Acessórios"]


class WardrobeState(AuthState):
    """Remote wardrobe with an account-partitioned local cache."""

    wardrobe_search: str = ""
    wardrobe_filter: str = "Todas"
    new_item_name: str = ""
    new_item_category: str = "Partes de cima"
    show_item_form: bool = False
    wardrobe_error: str = ""
    wardrobe_remote_ready: bool = False
    wardrobe_sync_notice: str = ""
    pending_item_local_id: str = ""
    pending_item_name: str = ""
    pending_item_category: str = ""

    def _read_wardrobe_store(self) -> dict[str, list[dict[str, str]]]:
        try:
            stored = json.loads(self.wardrobe_storage or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}

        if isinstance(stored, dict):
            return {
                str(owner_id): [item for item in items if isinstance(item, dict)]
                for owner_id, items in stored.items()
                if isinstance(items, list)
            }
        return {}

    def _persist_wardrobe_items(self):
        if not self.wardrobe_owner_id:
            return
        stored = self._read_wardrobe_store()
        stored[self.wardrobe_owner_id] = self.wardrobe_items
        self.wardrobe_storage = json.dumps(stored, ensure_ascii=False)

    def _normalize_wardrobe_item(self, item: dict) -> dict[str, str]:
        local_id = str(item.get("chave_local") or item.get("local_id") or item.get("id") or uuid.uuid4().hex)
        return {
            "id": str(item.get("id") or local_id),
            "local_id": local_id,
            "name": str(item.get("nome") or item.get("name") or "Peça sem nome"),
            "category": str(item.get("categoria") or item.get("category") or WARDROBE_CATEGORIES[0]),
            "status": str(item.get("status") or "No armário"),
            "synced": "true" if item.get("chave_local") or item.get("synced") == "true" else "false",
        }

    @rx.var
    def filtered_items(self) -> list[dict[str, str]]:
        search = self.wardrobe_search.strip().casefold()
        return [
            item
            for item in self.wardrobe_items
            if (self.wardrobe_filter == "Todas" or item.get("category") == self.wardrobe_filter)
            and (not search or search in item.get("name", "").casefold())
        ]

    @rx.var
    def wardrobe_count(self) -> int:
        return len(self.wardrobe_items)

    async def load_wardrobe(self):
        """Valida a sessão e separa as peças salvas por usuário."""
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")

        owner_id = str(self.current_user.get("id", ""))
        if not owner_id:
            self.wardrobe_items = []
            self.wardrobe_owner_id = ""
            return rx.redirect("/login")

        self.wardrobe_owner_id = owner_id
        stored = self._read_wardrobe_store()
        cached = [self._normalize_wardrobe_item(item) for item in stored.get(owner_id, [])]
        self.wardrobe_items = cached
        self.wardrobe_remote_ready = False
        self.wardrobe_sync_notice = "Armário sem sincronização; mantendo os dados deste navegador."
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meuArmario",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
                if response.status_code in (401, 403):
                    self.auth_token = ""
                    self.account_validated = False
                    return rx.redirect("/login")
                if response.status_code == 404:
                    self.wardrobe_sync_notice = "API do armário ainda não publicada; seus itens locais estão preservados."
                    return
                response.raise_for_status()
                payload = response.json()
                raw_items = payload.get("itens", []) if isinstance(payload, dict) else payload
                if not isinstance(raw_items, list):
                    raise ValueError("Formato inesperado do armário.")
                remote_items = [self._normalize_wardrobe_item(item) for item in raw_items if isinstance(item, dict)]
                remote_keys = {item["local_id"] for item in remote_items}
                unsynced_local = []
                migration_failed = False
                for local_item in cached:
                    local_key = local_item["local_id"]
                    if local_key in remote_keys:
                        continue
                    try:
                        migration_response = await client.post(
                            f"{XANO_PDB}/meuArmario",
                            headers={"Authorization": f"Bearer {self.auth_token}"},
                            json={
                                "chave_local": local_key,
                                "nome": local_item["name"],
                                "categoria": local_item["category"],
                            },
                        )
                        if migration_response.status_code in (401, 403):
                            self.auth_token = ""
                            self.account_validated = False
                            return rx.redirect("/login")
                        migration_response.raise_for_status()
                        saved = migration_response.json()
                        if isinstance(saved, dict) and isinstance(saved.get("item"), dict):
                            saved = saved["item"]
                        if not isinstance(saved, dict) or not saved.get("id"):
                            raise ValueError("Resposta inesperada ao migrar uma peça.")
                        remote_items.append(self._normalize_wardrobe_item(saved))
                        remote_keys.add(local_key)
                    except (httpx.HTTPError, ValueError):
                        migration_failed = True
                        unsynced_local.append(local_item)
                self.wardrobe_items = [*remote_items, *unsynced_local]
                self.wardrobe_remote_ready = True
                self.wardrobe_sync_notice = (
                    "Parte das peças continua apenas neste navegador; tente recarregar para sincronizar."
                    if migration_failed else "Armário sincronizado com sua conta."
                )
                self._persist_wardrobe_items()
        except (httpx.HTTPError, ValueError):
            self.wardrobe_sync_notice = "Sem conexão com o Xano; exibindo o cache local desta conta."

    def set_wardrobe_search(self, value: str):
        self.wardrobe_search = value

    def set_wardrobe_filter(self, value: str):
        self.wardrobe_filter = value

    def reset_wardrobe_filters(self):
        self.wardrobe_search = ""
        self.wardrobe_filter = "Todas"

    def set_new_item_name(self, value: str):
        self.new_item_name = value
        self.wardrobe_error = ""
        if value.strip() != self.pending_item_name:
            self.pending_item_local_id = ""

    def set_new_item_category(self, value: str):
        self.new_item_category = value
        if value != self.pending_item_category:
            self.pending_item_local_id = ""

    def toggle_item_form(self):
        self.show_item_form = not self.show_item_form
        self.wardrobe_error = ""

    async def add_item(self):
        name = self.new_item_name.strip()
        category = self.new_item_category
        if not name:
            self.wardrobe_error = "Informe o nome da peca antes de salvar."
            return
        if not self.pending_item_local_id or name != self.pending_item_name or category != self.pending_item_category:
            self.pending_item_local_id = uuid.uuid4().hex
            self.pending_item_name = name
            self.pending_item_category = category
        local_id = self.pending_item_local_id
        item = {
            "id": local_id, "local_id": local_id, "name": name,
            "category": category, "status": "No armario", "synced": "false",
        }
        if self.wardrobe_remote_ready:
            try:
                async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                    response = await client.post(
                        f"{XANO_PDB}/meuArmario",
                        headers={"Authorization": f"Bearer {self.auth_token}"},
                        json={"chave_local": local_id, "nome": name, "categoria": category},
                    )
                if response.status_code in (401, 403):
                    self.auth_token = ""
                    self.account_validated = False
                    return rx.redirect("/login")
                response.raise_for_status()
                saved = response.json()
                if isinstance(saved, dict) and isinstance(saved.get("item"), dict):
                    saved = saved["item"]
                if not isinstance(saved, dict) or not saved.get("id"):
                    raise ValueError("Resposta inesperada ao salvar a peca.")
                item = self._normalize_wardrobe_item(saved)
                self.wardrobe_sync_notice = "Peca salva e sincronizada com sua conta."
            except (httpx.HTTPError, ValueError):
                self.wardrobe_error = "Nao foi possivel sincronizar a peca. Tente novamente."
                return
        else:
            self.wardrobe_sync_notice = "Peca salva neste navegador; ainda nao sincronizada com o Xano."
        self.wardrobe_items = [item, *self.wardrobe_items]
        self._persist_wardrobe_items()
        self.new_item_name = ""
        self.show_item_form = False
        self.wardrobe_error = ""
        self.pending_item_local_id = ""
        self.pending_item_name = ""
        self.pending_item_category = ""

    async def remove_item(self, item_id: str):
        item = next((row for row in self.wardrobe_items if row.get("id") == str(item_id)), None)
        if not item:
            return
        if self.wardrobe_remote_ready and item.get("synced") == "true":
            try:
                async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                    response = await client.delete(
                        f"{XANO_PDB}/meuArmario/{item_id}",
                        headers={"Authorization": f"Bearer {self.auth_token}"},
                    )
                if response.status_code in (401, 403):
                    self.auth_token = ""
                    self.account_validated = False
                    return rx.redirect("/login")
                response.raise_for_status()
            except httpx.HTTPError:
                self.wardrobe_error = "Nao foi possivel remover a peca sincronizada."
                return
        self.wardrobe_items = [row for row in self.wardrobe_items if row.get("id") != str(item_id)]
        self._persist_wardrobe_items()
        self.wardrobe_error = ""



# ── Estado de Gerenciamento de Endereços (AddressState) ─────────────────
VIACEP_URL   = "https://viacep.com.br/ws/{cep}/json/"

class AddressItem(typing.TypedDict, total=False):
    id: int
    cliente_id: int
    logradouro: str
    numero: str
    complemento: str
    bairro: str
    referencia: str
    padrao: bool
    cep: str
    cidade: str
    uf: str
    _cep: dict[str, str]


class AddressState(AuthState):
    """Estado para gestão completa de endereços do cliente."""

    # Lista de endereços do cliente
    addresses: list[AddressItem] = []

    # Formulário de novo endereço
    form_cep: str = ""
    form_logradouro: str = ""
    form_numero: str = ""
    form_complemento: str = ""
    form_bairro: str = ""
    form_referencia: str = ""
    form_uf: str = ""
    form_cidade: str = ""
    form_padrao: bool = False

    # Controles visuais
    cep_loading: bool = False
    cep_error: str = ""
    address_loading: bool = False
    address_error: str = ""
    address_success: str = ""
    show_form: bool = False
    editing_id: int = 0

    # ── setters do formulário ────────────────────────────────────────────
    def set_form_cep(self, v: str):
        self.form_cep = re.sub(r"\D", "", v)[:8]
        self.cep_error = ""

    def set_form_logradouro(self, v: str): self.form_logradouro = v
    def set_form_numero(self, v: str): self.form_numero = v
    def set_form_complemento(self, v: str): self.form_complemento = v
    def set_form_bairro(self, v: str): self.form_bairro = v
    def set_form_referencia(self, v: str): self.form_referencia = v
    def set_form_padrao(self, v: bool): self.form_padrao = v

    def toggle_form(self):
        """Alterna exibição do formulário e limpa os campos."""
        self.show_form = not self.show_form
        if not self.show_form:
            self._clear_form()

    def _clear_form(self):
        self.form_cep = ""
        self.form_logradouro = ""
        self.form_numero = ""
        self.form_complemento = ""
        self.form_bairro = ""
        self.form_referencia = ""
        self.form_uf = ""
        self.form_cidade = ""
        self.form_padrao = False
        self.cep_error = ""
        self.address_error = ""
        self.address_success = ""
        self.editing_id = 0

    # ── load endereços ao entrar na rota ────────────────────────────────
    async def load_addresses(self):
        """Guard + carrega lista de endereços do cliente autenticado."""
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        self.address_loading = True
        self.address_error = ""
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as c:
                r = await c.get(
                    f"{XANO_PDB}/consultaEnderecoDoCliente",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            if r.status_code == 200:
                data = r.json()
                self.addresses = data.get("endereco1", [])
            else:
                self.address_error = "Erro ao carregar endereços."
        except httpx.TimeoutException:
            self.address_error = "Servidor demorou a responder."
        except httpx.RequestError:
            self.address_error = "Erro de conexão."
        finally:
            self.address_loading = False

    # ── busca CEP via ViaCEP + upsert no Xano ───────────────────────────
    async def buscar_cep(self):
        """Consulta ViaCEP e preenche automaticamente cidade/UF/logradouro."""
        cep = re.sub(r"\D", "", self.form_cep)
        if len(cep) != 8:
            self.cep_error = "Digite um CEP válido com 8 dígitos."
            return
        self.cep_loading = True
        self.cep_error = ""
        try:
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.get(VIACEP_URL.format(cep=cep))
            if r.status_code != 200 or r.json().get("erro"):
                self.cep_error = "CEP não encontrado. Verifique e tente novamente."
                return
            data = r.json()
            self.form_logradouro  = data.get("logradouro", "") or self.form_logradouro
            self.form_bairro      = data.get("bairro", "")     or self.form_bairro
            self.form_cidade      = data.get("localidade", "")
            self.form_uf          = data.get("uf", "")
        except Exception:
            self.cep_error = "Falha na consulta do CEP. Tente novamente."
        finally:
            self.cep_loading = False

    # ── salvar / atualizar endereço ──────────────────────────────────────
    async def salvar_endereco(self):
        """Salva um novo endereço ou atualiza o existente via Xano."""
        # validações básicas
        if not self.form_logradouro.strip():
            self.address_error = "Logradouro é obrigatório."
            return
        if not self.form_numero.strip():
            self.address_error = "Número é obrigatório."
            return
        if len(re.sub(r"\D", "", self.form_cep)) != 8:
            self.address_error = "Informe um CEP válido antes de salvar."
            return

        self.address_loading = True
        self.address_error = ""
        self.address_success = ""

        payload = {
            "logradouro" : self.form_logradouro.strip(),
            "numero"     : self.form_numero.strip(),
            "complemento": self.form_complemento.strip(),
            "bairro"     : self.form_bairro.strip(),
            "referencia" : self.form_referencia.strip(),
            "padrao"     : self.form_padrao,
            "cep"        : re.sub(r"\D", "", self.form_cep),
            "uf"         : self.form_uf,
            "cidade"     : self.form_cidade,
        }

        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as c:
                if self.editing_id > 0:
                    payload["endereco_id"] = self.editing_id
                    r = await c.patch(
                        f"{XANO_PDB}/atualizaEndereco",
                        json=payload,
                        headers={"Authorization": f"Bearer {self.auth_token}"},
                    )
                else:
                    r = await c.post(
                        f"{XANO_PDB}/salvaEndereco",
                        json=payload,
                        headers={"Authorization": f"Bearer {self.auth_token}"},
                    )

            if r.status_code == 200:
                self.address_success = (
                    "Endereço atualizado com sucesso!" if self.editing_id > 0
                    else "Endereço salvo com sucesso!"
                )
                self._clear_form()
                self.show_form = False
                # recarrega lista
                async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as c:
                    r2 = await c.get(
                        f"{XANO_PDB}/consultaEnderecoDoCliente",
                        headers={"Authorization": f"Bearer {self.auth_token}"},
                    )
                if r2.status_code == 200:
                    self.addresses = r2.json().get("endereco1", [])
            else:
                body = r.json()
                self.address_error = body.get("message", "Erro ao salvar endereço.")
        except httpx.TimeoutException:
            self.address_error = "Servidor demorou a responder."
        except httpx.RequestError:
            self.address_error = "Erro de conexão."
        finally:
            self.address_loading = False

    # ── marcar como padrão ───────────────────────────────────────────────
    async def marcar_padrao(self, endereco_id: int):
        """Marca o endereço como padrão de entrega."""
        self.address_loading = True
        self.address_error = ""
        self.address_success = ""
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as c:
                r = await c.patch(
                    f"{XANO_PDB}/marcarEnderecoPadrao",
                    json={"endereco_id": endereco_id},
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            if r.status_code == 200:
                self.address_success = "Endereço padrão atualizado!"
                async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as c:
                    r2 = await c.get(
                        f"{XANO_PDB}/consultaEnderecoDoCliente",
                        headers={"Authorization": f"Bearer {self.auth_token}"},
                    )
                if r2.status_code == 200:
                    self.addresses = r2.json().get("endereco1", [])
            else:
                self.address_error = "Falha ao definir endereço padrão."
        except Exception:
            self.address_error = "Erro de conexão."
        finally:
            self.address_loading = False

    # ── preencher formulário para edição ─────────────────────────────────
    def editar_endereco(self, endereco: dict):
        """Preenche o formulário com os dados do endereço para edição."""
        self.editing_id       = endereco.get("id", 0)
        self.form_logradouro  = endereco.get("logradouro", "")
        self.form_numero      = endereco.get("numero", "")
        self.form_complemento = endereco.get("complemento", "")
        self.form_bairro      = endereco.get("bairro", "")
        self.form_referencia  = endereco.get("referencia", "")
        self.form_padrao      = endereco.get("padrao", False)
        cep_data              = endereco.get("_cep", {})
        self.form_cep         = cep_data.get("cep", "")
        self.form_cidade      = cep_data.get("cidade", "")
        self.form_uf          = cep_data.get("uf", "")
        self.show_form        = True
        self.address_error    = ""
        self.address_success  = ""


# ── Componentes de UI ────────────────────────────────────────────────────
INPUT_STYLE = {
    "background": "#FFFFFF",
    "border": "1px solid rgba(15,26,51,0.18)",
    "border_radius": "12px",
    "color": INK,
    "height": "46px",
    "width": "100%",
    "padding_left": "14px",
    "padding_right": "14px",
    "font_size": "0.95rem",
    "_focus": {
        "border_color": THREAD,
        "box_shadow": "0 0 0 3px rgba(233,162,59,0.25)",
        "outline": "none",
    },
}

def _format_brl(value: Decimal) -> str:
    formatted = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


class StoreState(AuthState):
    """Catálogo de vestuário Xano e sacola local, sem criar pedidos nesta etapa."""

    products: list[dict[str, str]] = []
    selected_product: dict[str, str] = {}
    cart_items: list[dict[str, str]] = []
    cart_storage: str = rx.LocalStorage("[]", name="osd_store_cart", sync=True)
    store_search: str = ""
    category_filter: str = "Todas"
    availability_filter: str = "Todos"
    price_sort: str = "Recomendados"
    catalog_loading: bool = False
    catalog_error: str = ""
    catalog_setup_required: bool = False
    catalog_unclassified_count: int = 0
    product_loading: bool = False
    product_error: str = ""
    cart_feedback: str = ""

    def _normalize_category(self, raw_category: object) -> str:
        value = unicodedata.normalize("NFKD", str(raw_category or "").casefold())
        value = "".join(char for char in value if not unicodedata.combining(char))
        value = re.sub(r"[^a-z0-9]+", " ", value).strip()
        if any(token in value for token in (
            "calcado", "sapato", "tenis", "sandalia", "bota", "chinelo",
        )):
            return "Calçados"
        if any(token in value for token in (
            "roupa", "vestuario", "camiseta", "camisa", "calca", "vestido", "saia",
            "blusa", "casaco", "jaqueta", "bermuda", "short", "sueter", "moletom",
            "macacao", "lingerie", "uniforme",
        )):
            return "Roupas"
        if any(token in value for token in (
            "acessorio", "bolsa", "cinto", "carteira", "chapeu", "bone", "joia", "bijuteria",
        )):
            return "Acessórios"
        return ""

    def _normalize_product(self, item: dict) -> dict[str, str]:
        raw_price = item.get("Preco", 0)
        try:
            price = Decimal(str(raw_price or 0).replace(",", "."))
        except (InvalidOperation, AttributeError):
            price = Decimal("0")
        stock = max(0, int(item.get("Qtd_Disp") or 0))
        made_to_order = str(item.get("Precisa_Produzir") or "").lower() in {"true", "1", "sim"}
        category = self._normalize_category(
            item.get("Categoria") or item.get("categoria") or item.get("category") or item.get("Category")
        )
        if stock > 0:
            availability = "Disponível agora"
        elif made_to_order:
            availability = "Sob encomenda"
        else:
            availability = "Sem estoque"
        return {
            "id": str(item.get("id", "")),
            "name": str(item.get("Nome") or "Produto sem nome"),
            "description": str(item.get("Descricao") or ""),
            "category": category,
            "stock": str(stock),
            "image_url": str(item.get("Url_Imagem") or ""),
            "price": str(price),
            "price_display": _format_brl(price),
            "made_to_order": "true" if made_to_order else "false",
            "availability": availability,
        }

    def _load_cart_from_storage(self):
        try:
            stored = json.loads(self.cart_storage or "[]")
        except (TypeError, json.JSONDecodeError):
            stored = []
        if not isinstance(stored, list):
            stored = []
        cart = []
        for item in stored:
            if not isinstance(item, dict) or not item.get("product_id"):
                continue
            try:
                quantity = max(1, min(99, int(item.get("quantity", 1))))
                price = Decimal(str(item.get("price", "0")).replace(",", "."))
            except (TypeError, ValueError, InvalidOperation):
                continue
            cart.append({
                "product_id": str(item["product_id"]),
                "name": str(item.get("name") or "Produto"),
                "price": str(price),
                "price_display": _format_brl(price),
                "image_url": str(item.get("image_url") or ""),
                "category": str(item.get("category") or ""),
                "availability": str(item.get("availability") or "Disponibilidade a confirmar"),
                "quantity": str(quantity),
            })
        self.cart_items = cart

    def _persist_cart(self):
        self.cart_storage = json.dumps(self.cart_items, ensure_ascii=False)

    def _sync_cart_prices(self):
        current = {item["id"]: item for item in self.products}
        updated = []
        for line in self.cart_items:
            product = current.get(line["product_id"])
            if product:
                updated.append({
                    **line,
                    "name": product["name"],
                    "price": product["price"],
                    "price_display": product["price_display"],
                    "image_url": product["image_url"],
                    "category": product["category"],
                    "availability": product["availability"],
                })
            else:
                updated.append(line)
        self.cart_items = updated
        self._persist_cart()

    @rx.var
    def filtered_products(self) -> list[dict[str, str]]:
        query = self.store_search.strip().casefold()
        visible = [
            product for product in self.products
            if (not query or query in product["name"].casefold() or query in product["description"].casefold())
            and (self.category_filter == "Todas" or product["category"] == self.category_filter)
            and (self.availability_filter == "Todos"
                 or product["availability"] == self.availability_filter)
        ]
        if self.price_sort == "Menor preço":
            visible.sort(key=lambda product: Decimal(product["price"]))
        elif self.price_sort == "Maior preço":
            visible.sort(key=lambda product: Decimal(product["price"]), reverse=True)
        return visible

    @rx.var
    def cart_count(self) -> int:
        return sum(int(item.get("quantity", "0")) for item in self.cart_items)

    @rx.var
    def cart_total_display(self) -> str:
        total = sum(
            Decimal(item.get("price", "0")) * int(item.get("quantity", "0"))
            for item in self.cart_items
        )
        return _format_brl(total)

    def set_store_search(self, value: str):
        self.store_search = value

    def set_availability_filter(self, value: str):
        self.availability_filter = value

    def set_category_filter(self, value: str):
        self.category_filter = value

    def set_price_sort(self, value: str):
        self.price_sort = value

    async def load_catalog(self):
        self.catalog_loading = True
        self.catalog_error = ""
        self.catalog_setup_required = False
        self.catalog_unclassified_count = 0
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(f"{XANO_DB}/produto")
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                payload = payload.get("produto", payload.get("PRODUTO", []))
            if not isinstance(payload, list):
                raise ValueError("Formato inesperado recebido do catálogo.")
            normalized_products = [
                self._normalize_product(item)
                for item in payload
                if isinstance(item, dict) and item.get("id") is not None
            ]
            self.catalog_unclassified_count = sum(not item["category"] for item in normalized_products)
            self.products = [item for item in normalized_products if item["category"]]
            self.catalog_setup_required = bool(normalized_products) and not self.products
            self._sync_cart_prices()
        except (httpx.HTTPError, ValueError) as exc:
            self.catalog_error = "Não foi possível carregar o catálogo agora. Tente novamente."
            print(f"Falha ao carregar catálogo Xano: {exc}")
        finally:
            self.catalog_loading = False

    async def load_store(self):
        await self.restore_session()
        self._load_cart_from_storage()
        await self.load_catalog()

    async def load_product_page(self):
        await self.restore_session()
        self._load_cart_from_storage()
        self.product_loading = True
        self.product_error = ""
        self.selected_product = {}
        product_id = str(self.router.url.query_parameters.get("id", ""))
        if not product_id.isdigit():
            self.product_error = "Este produto não está disponível."
            self.product_loading = False
            return
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(f"{XANO_DB}/produto/{product_id}")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("id") is None:
                raise ValueError("Produto não encontrado.")
            normalized_product = self._normalize_product(payload)
            if not normalized_product["category"]:
                raise ValueError("Produto sem categoria de vestuário.")
            self.selected_product = normalized_product
        except (httpx.HTTPError, ValueError):
            self.product_error = "Não encontramos esse produto no catálogo."
        finally:
            self.product_loading = False

    async def load_cart_page(self):
        await self.restore_session()
        self._load_cart_from_storage()
        await self.load_catalog()

    def open_product(self, product_id: str):
        return rx.redirect(f"/produto?id={product_id}")

    def add_to_cart(self, product_id: str):
        product = next((item for item in self.products if item["id"] == str(product_id)), None)
        if not product:
            product = self.selected_product if self.selected_product.get("id") == str(product_id) else None
        if not product:
            self.cart_feedback = "Carregue novamente o catálogo antes de adicionar este produto."
            return
        if product["availability"] == "Sem estoque":
            self.cart_feedback = "Este produto está indisponível no momento."
            return
        self.cart_feedback = ""
        self._load_cart_from_storage()
        existing = next((item for item in self.cart_items if item["product_id"] == str(product_id)), None)
        if existing:
            quantity = int(existing["quantity"])
            stock = int(product["stock"])
            if stock > 0 and quantity >= stock:
                self.cart_feedback = "Você já adicionou todo o estoque disponível deste produto."
                return
            existing["quantity"] = str(quantity + 1)
            existing.update({
                "name": product["name"], "price": product["price"],
                "price_display": product["price_display"], "image_url": product["image_url"],
                "category": product["category"],
                "availability": product["availability"],
            })
        else:
            self.cart_items = [*self.cart_items, {
                "product_id": product["id"], "name": product["name"],
                "price": product["price"], "price_display": product["price_display"],
                "image_url": product["image_url"], "category": product["category"],
                "availability": product["availability"],
                "quantity": "1",
            }]
        self._persist_cart()
        self.cart_feedback = f"{product['name']} foi adicionado à sua sacola."

    def increment_cart_item(self, product_id: str):
        product = next((item for item in self.products if item["id"] == str(product_id)), None)
        for item in self.cart_items:
            if item["product_id"] == str(product_id):
                quantity = int(item["quantity"])
                stock = int(product["stock"]) if product else 0
                if stock > 0 and quantity >= stock:
                    self.cart_feedback = "Você já adicionou todo o estoque disponível deste produto."
                    return
                item["quantity"] = str(min(99, quantity + 1))
                self._persist_cart()
                return

    def decrement_cart_item(self, product_id: str):
        for item in self.cart_items:
            if item["product_id"] == str(product_id) and int(item["quantity"]) > 1:
                item["quantity"] = str(int(item["quantity"]) - 1)
                self._persist_cart()
                return

    def remove_cart_item(self, product_id: str):
        self.cart_items = [item for item in self.cart_items if item["product_id"] != str(product_id)]
        self._persist_cart()
        self.cart_feedback = "Produto removido da sacola."


class OrdersState(AuthState):
    """Checkout PIX e consultas privadas de pedidos pelo Xano."""

    cart_storage: str = rx.LocalStorage("[]", name="osd_store_cart", sync=True)
    idempotency_storage: str = rx.LocalStorage("", name="osd_checkout_idempotency_key", sync=True)
    idempotency_cart_storage: str = rx.LocalStorage("", name="osd_checkout_cart_fingerprint", sync=True)
    checkout_addresses: list[dict[str, str]] = []
    selected_address_id: str = ""
    checkout_loading: bool = False
    checkout_submitting: bool = False
    checkout_error: str = ""
    checkout_notice: str = ""
    checkout_complete: bool = False
    checkout_order_id: str = ""
    pix_payload: str = ""
    pix_encoded_image: str = ""
    orders: list[dict[str, str]] = []
    order_loading: bool = False
    order_error: str = ""
    order_detail: dict[str, str] = {}
    order_items: list[dict[str, str]] = []

    def _cart_lines(self) -> list[dict[str, int]]:
        try:
            raw = json.loads(self.cart_storage or "[]")
        except (TypeError, json.JSONDecodeError):
            raw = []
        if not isinstance(raw, list):
            return []
        lines = []
        for item in raw:
            if not isinstance(item, dict) or not str(item.get("product_id", "")).isdigit():
                continue
            if item.get("category") not in STORE_CATEGORIES:
                return []
            try:
                quantity = int(item.get("quantity", 0))
            except (TypeError, ValueError):
                continue
            if 1 <= quantity <= 99:
                lines.append({"produto_id": int(item["product_id"]), "qtd": quantity})
        return lines

    def _cart_has_unclassified_items(self) -> bool:
        try:
            raw = json.loads(self.cart_storage or "[]")
        except (TypeError, json.JSONDecodeError):
            return False
        return isinstance(raw, list) and any(
            isinstance(item, dict)
            and str(item.get("product_id", "")).isdigit()
            and item.get("category") not in STORE_CATEGORIES
            for item in raw
        )

    def _ensure_idempotency_key(self):
        fingerprint = json.dumps(
            {"endereco_id": str(self.selected_address_id or ""), "itens": self._cart_lines()},
            sort_keys=True, separators=(",", ":"),
        )
        if not self.idempotency_storage or self.idempotency_cart_storage != fingerprint:
            self.idempotency_storage = uuid.uuid4().hex
            self.idempotency_cart_storage = fingerprint

    @rx.var
    def checkout_cart_count(self) -> int:
        return sum(item["qtd"] for item in self._cart_lines())

    @rx.var
    def checkout_address_options(self) -> list[str]:
        return [f"{item['id']} · {item['label']}" for item in self.checkout_addresses]

    @rx.var
    def selected_checkout_address(self) -> str:
        match = next((item for item in self.checkout_addresses if item["id"] == self.selected_address_id), None)
        return f"{match['id']} · {match['label']}" if match else ""

    async def load_checkout(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        self.checkout_loading = True
        self.checkout_error = ""
        self.checkout_notice = ""
        self.checkout_complete = False
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/consultaEnderecoDoCliente",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("endereco1", []) if isinstance(payload, dict) else []
            options = []
            default_id = ""
            for address in rows:
                if not isinstance(address, dict) or not address.get("id"):
                    continue
                cep = address.get("_cep") or {}
                city_state = " / ".join(x for x in [str(cep.get("cidade") or ""), str(cep.get("uf") or "")] if x)
                label = " · ".join(x for x in [
                    f"{address.get('logradouro') or 'Endereço'} {address.get('numero') or ''}".strip(),
                    str(address.get("bairro") or ""), city_state,
                ] if x)
                if address.get("padrao"):
                    label += " (padrão)"
                    default_id = str(address["id"])
                options.append({"id": str(address["id"]), "label": label})
            self.checkout_addresses = options
            if self.selected_address_id not in {item["id"] for item in options}:
                self.selected_address_id = default_id or (options[0]["id"] if options else "")
            self._ensure_idempotency_key()
            if not options:
                self.checkout_notice = "Cadastre um endereço antes de continuar."
            if self._cart_has_unclassified_items():
                self.checkout_notice = "A sacola contém itens antigos sem categoria de moda. Remova-os e adicione novamente os produtos válidos da loja."
        except (httpx.HTTPError, ValueError):
            self.checkout_error = "Não foi possível carregar seus endereços. Tente novamente."
        finally:
            self.checkout_loading = False

    def select_checkout_address(self, value: str):
        next_address_id = value.split(" · ", 1)[0]
        if next_address_id != self.selected_address_id:
            self.selected_address_id = next_address_id
            self._ensure_idempotency_key()
        self.checkout_error = ""

    async def submit_checkout(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        lines = self._cart_lines()
        if not lines:
            self.checkout_error = (
                "A sacola contém itens sem categoria de moda válida. Remova-os e adicione novamente os produtos da loja."
                if self._cart_has_unclassified_items()
                else "Sua sacola está vazia. Volte à loja para escolher produtos."
            )
            return
        if not self.selected_address_id.isdigit():
            self.checkout_error = "Selecione um endereço de entrega válido."
            return
        self._ensure_idempotency_key()
        self.checkout_submitting = True
        self.checkout_error = ""
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(
                    f"{XANO_PDB}/checkoutPedido",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                    json={
                        "endereco_id": int(self.selected_address_id),
                        "tipo": "PIX",
                        "itens": lines,
                        "chave_idempotencia": self.idempotency_storage,
                    },
                )
            if response.status_code == 404:
                self.checkout_error = "O checkout seguro ainda não está publicado no Xano. Nenhum pedido ou pagamento foi criado."
                return
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("pedido"), dict):
                raise ValueError("Pedido ausente na resposta do checkout.")
            payment = payload.get("cobranca")
            if not isinstance(payment, dict):
                raise ValueError("Cobrança ausente na resposta do checkout.")
            order_id = str(payload["pedido"].get("id", ""))
            payment_id = str(payment.get("id") or payment.get("idpayment") or "")
            pix_payload = str(payment.get("payload") or payment.get("pixCopiaECola") or "")
            pix_encoded_image = str(payment.get("encodedImage") or "")
            if not order_id or not payment_id or not (pix_payload or pix_encoded_image):
                self.checkout_error = "O checkout não retornou um pedido e uma instrução PIX válidos. A sacola e a chave da tentativa foram preservadas."
                return
            self.checkout_order_id = order_id
            self.pix_payload = pix_payload
            self.pix_encoded_image = pix_encoded_image
            self.checkout_complete = True
            if self.checkout_complete:
                self.cart_storage = "[]"
                self.idempotency_storage = ""
                self.idempotency_cart_storage = ""
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                self.checkout_error = "Sua sessão expirou. Entre novamente para continuar."
                self.auth_token = ""
                self.account_validated = False
            else:
                self.checkout_error = "Não foi possível confirmar o pedido. Revise os dados e tente novamente."
        except (httpx.RequestError, ValueError):
            self.checkout_error = "Não foi possível conectar ao checkout. A chave da tentativa foi preservada para evitar duplicidade."
        finally:
            self.checkout_submitting = False

    async def load_orders(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        self.order_loading = True
        self.order_error = ""
        self.orders = []
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meusPedidos",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            if response.status_code == 404:
                self.order_error = "O histórico de pedidos ainda não está publicado no Xano."
                return
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("pedidos", []) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                raise ValueError("Formato de pedidos inválido.")
            self.orders = [{
                "id": str(row.get("id", "")),
                "total": str(row.get("Total", row.get("total", "0"))),
                "status": str(row.get("status", {}).get("status") if isinstance(row.get("status"), dict) else row.get("status") or row.get("status_pedido_id") or "Em processamento"),
                "created_at": str(row.get("created_at") or ""),
            } for row in rows if isinstance(row, dict) and row.get("id") is not None]
        except (httpx.HTTPError, ValueError):
            self.order_error = "Não foi possível carregar seus pedidos agora. Tente novamente."
        finally:
            self.order_loading = False

    async def load_order_detail(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        order_id = str(self.router.url.query_parameters.get("id", ""))
        self.order_detail = {}
        self.order_items = []
        self.order_error = ""
        if not order_id.isdigit():
            self.order_error = "Este pedido não foi encontrado."
            return
        self.order_loading = True
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meuPedido/{order_id}",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            if response.status_code == 404:
                self.order_error = "O detalhe de pedidos ainda não está publicado no Xano."
                return
            response.raise_for_status()
            payload = response.json()
            order = payload.get("pedido", {}) if isinstance(payload, dict) else {}
            if not isinstance(order, dict) or not order.get("id"):
                raise ValueError("Pedido ausente.")
            status = order.get("status") or payload.get("status") or {}
            self.order_detail = {
                "id": str(order["id"]),
                "total": str(order.get("Total", order.get("total", "0"))),
                "status": str(status.get("status") if isinstance(status, dict) else status or order.get("status_pedido_id") or "Em processamento"),
                "created_at": str(order.get("created_at") or ""),
            }
            raw_items = payload.get("itens", []) if isinstance(payload, dict) else []
            if isinstance(raw_items, list):
                self.order_items = [{
                    "name": str(item.get("produto", {}).get("Nome") if isinstance(item.get("produto"), dict) else item.get("Nome") or f"Produto {item.get('produto_id', '')}"),
                    "quantity": str(item.get("Qtd", item.get("qtd", "1"))),
                    "subtotal": str(item.get("Subtotal", item.get("subtotal", "0"))),
                } for item in raw_items if isinstance(item, dict)]
        except (httpx.HTTPError, ValueError):
            self.order_error = "Não foi possível carregar este pedido."
        finally:
            self.order_loading = False


ARTICLE_CONTENT = [
    {
        "id": "look-com-intencao",
        "title": "Monte menos looks. Use melhor o que você já tem.",
        "category": "ESTILO PESSOAL",
        "summary": "Um método simples para transformar peças conhecidas em combinações que parecem novas.",
        "reading_time": "4 min",
        "body": "Comece por uma peça que você gosta e usa pouco. Escolha uma base confortável, acrescente uma camada e finalize com um detalhe que traduza o seu dia.\n\nFotografe a combinação no armário digital. Na próxima semana, tente trocar apenas uma peça. O objetivo não é comprar mais, é encontrar novas possibilidades no que já faz parte da sua rotina.",
    },
    {
        "id": "armario-de-estacao",
        "title": "Uma troca de estação sem perder o que funciona.",
        "category": "GUARDA-ROUPA INTELIGENTE",
        "summary": "Organize por frequência, conforto e contexto em vez de esconder tudo que não está na moda.",
        "reading_time": "5 min",
        "body": "Separe as peças que você realmente usa das que precisam de cuidado. Deixe itens versáteis acessíveis e registre combinações que funcionam para o seu clima.\n\nUma peça fora de estação ainda pode servir em camadas. Antes de guardar, confira a etiqueta, limpe e escolha um lugar seco. Reavalie quando a rotina mudar.",
    },
    {
        "id": "cuidado-que-dura",
        "title": "Pequenos cuidados que prolongam a vida das roupas.",
        "category": "CUIDADO E REUSO",
        "summary": "Lavagem, secagem e armazenamento começam pela etiqueta e pelo tecido.",
        "reading_time": "3 min",
        "body": "Leia a etiqueta antes de lavar e agrupe peças por cor e necessidade de cuidado. Use ciclos mais suaves quando a orientação permitir e evite secagem agressiva em tecidos delicados.\n\nConserte um botão ou uma costura assim que perceber o problema. O cuidado mais adequado depende da peça e das instruções do fabricante.",
    },
]

INSPIRATION_IDEAS = [
    {"title": "Base neutra, textura viva", "tag": "DIA A DIA", "description": "Combine tons simples com uma textura que já está no seu armário.", "icon": "layers-3"},
    {"title": "Uma peça, três contextos", "tag": "REPETIR COM INTENÇÃO", "description": "Leve a mesma peça do trabalho ao fim de semana trocando a camada e o calçado.", "icon": "repeat-2"},
    {"title": "Cor em um só detalhe", "tag": "EXPERIMENTE", "description": "Comece com uma cor que você gosta em um acessório ou terceira peça.", "icon": "palette"},
]

WARDROBE_CHALLENGES = [
    {"id": "repeat-three", "title": "Três dias, uma peça favorita", "description": "Use a mesma peça em três combinações diferentes nesta semana.", "points": "30", "duration": "7 dias", "icon": "repeat-2"},
    {"id": "forgotten-piece", "title": "Resgate uma peça esquecida", "description": "Escolha algo pouco usado no armário e monte um look em volta dessa peça.", "points": "40", "duration": "15 min", "icon": "sparkles"},
    {"id": "care-routine", "title": "Um cuidado que faz diferença", "description": "Confira a etiqueta e cuide de uma peça que precisa de atenção.", "points": "20", "duration": "Hoje", "icon": "heart-handshake"},
    {"id": "plan-week", "title": "Planeje três combinações", "description": "Deixe três ideias prontas para os próximos dias usando seu acervo.", "points": "25", "duration": "20 min", "icon": "calendar-check-2"},
]


class ContentState(AuthState):
    challenge_storage: str = rx.LocalStorage("{}", name="osd_challenges_by_account", sync=True)
    completed_challenges: list[str] = []
    current_article: dict[str, str] = {}
    article_error: str = ""

    @rx.var
    def challenge_cards(self) -> list[dict[str, str]]:
        completed = set(self.completed_challenges)
        return [{**item, "completed": "true" if item["id"] in completed else "false"} for item in WARDROBE_CHALLENGES]

    @rx.var
    def challenge_points(self) -> int:
        points_by_id = {item["id"]: int(item["points"]) for item in WARDROBE_CHALLENGES}
        return sum(points_by_id.get(item_id, 0) for item_id in self.completed_challenges)

    @rx.var
    def challenge_completion_percent(self) -> int:
        return int(len(self.completed_challenges) / max(1, len(WARDROBE_CHALLENGES)) * 100)

    async def load_challenges(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        owner_id = str(self.current_user.get("id", ""))
        try:
            stored = json.loads(self.challenge_storage or "{}")
        except (TypeError, json.JSONDecodeError):
            stored = {}
        progress = stored.get(owner_id, []) if isinstance(stored, dict) else []
        self.completed_challenges = [item for item in progress if isinstance(item, str) and item in {challenge["id"] for challenge in WARDROBE_CHALLENGES}]

    def complete_challenge(self, challenge_id: str):
        if challenge_id not in {item["id"] for item in WARDROBE_CHALLENGES}:
            return
        if challenge_id in self.completed_challenges:
            return
        self.completed_challenges = [*self.completed_challenges, challenge_id]
        try:
            stored = json.loads(self.challenge_storage or "{}")
        except (TypeError, json.JSONDecodeError):
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        owner_id = str(self.current_user.get("id", ""))
        stored[owner_id] = self.completed_challenges
        self.challenge_storage = json.dumps(stored, ensure_ascii=False)

    async def load_article(self):
        await self.restore_session()
        article_id = str(self.router.url.query_parameters.get("id", ""))
        self.article_error = ""
        self.current_article = next((article for article in ARTICLE_CONTENT if article["id"] == article_id), {})
        if not self.current_article:
            self.article_error = "Não encontramos esse artigo."


class DeviceState(AuthState):
    """Client views for a future Xano-authorized device pairing flow."""

    devices: list[dict[str, str]] = []
    selected_device: dict[str, str] = {}
    device_loading: bool = False
    device_error: str = ""
    device_notice: str = ""
    pairing_identifier: str = ""
    pairing_loading: bool = False
    pairing_error: str = ""
    pairing_code: str = ""
    pairing_expires_at: str = ""
    device_events: list[dict[str, str]] = []

    def set_pairing_identifier(self, value: str):
        self.pairing_identifier = value.strip()[:100]
        self.pairing_error = ""

    @staticmethod
    def _normalize_device_status(value: Any) -> str:
        status = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
        if status in {"connected", "online", "ativo", "conectado"}:
            return "Conectado"
        if status in {"pending", "pairing", "pairing pending", "pending pairing", "pending_pairing", "pareamento pendente", "pendente"}:
            return "Pareamento pendente"
        return "Sem contato"

    async def load_pairing_page(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        self.pairing_identifier = ""
        self.pairing_error = ""
        self.pairing_code = ""
        self.pairing_expires_at = ""

    async def load_devices(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        self.device_loading = True
        self.device_error = ""
        self.device_notice = ""
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meusDispositivos",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            if response.status_code in (401, 403):
                self.auth_token = ""
                self.account_validated = False
                return rx.redirect("/login")
            if response.status_code == 404:
                self.devices = []
                self.device_notice = "Integração com dispositivos ainda não publicada; nenhum sensor está conectado."
                return
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("dispositivos", []) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                raise ValueError("Formato inesperado de dispositivos.")
            self.devices = [{
                "id": str(item.get("id", "")),
                "name": str(item.get("nome") or item.get("name") or "Armário inteligente"),
                "type": str(item.get("tipo") or item.get("type") or "Dispositivo"),
                "status": self._normalize_device_status(item.get("status")),
                "last_seen": str(item.get("ultimo_contato") or item.get("last_seen") or "Ainda sem leituras"),
            } for item in rows if isinstance(item, dict) and item.get("id") is not None]
            if not self.devices:
                self.device_notice = "Nenhum dispositivo conectado a esta conta."
        except (httpx.HTTPError, ValueError):
            self.device_error = "Não foi possível consultar os dispositivos. Tente novamente."
        finally:
            self.device_loading = False

    async def request_pairing(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        identifier = self.pairing_identifier.strip()
        if not identifier:
            self.pairing_error = "Informe o código impresso no dispositivo."
            return
        self.pairing_loading = True
        self.pairing_error = ""
        self.pairing_code = ""
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(
                    f"{XANO_PDB}/solicitarPareamento",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                    json={"identificador": identifier},
                )
            if response.status_code in (401, 403):
                self.auth_token = ""
                self.account_validated = False
                return rx.redirect("/login")
            if response.status_code == 404:
                self.pairing_error = "O serviço de pareamento ainda não está publicado no Xano. Nenhum dispositivo foi conectado."
                return
            response.raise_for_status()
            payload = response.json()
            self.pairing_code = str(payload.get("codigo_pareamento") or "")
            self.pairing_expires_at = str(payload.get("expira_em") or "")
            if not self.pairing_code:
                raise ValueError("Código de pareamento ausente.")
        except (httpx.HTTPError, ValueError):
            self.pairing_error = "Não foi possível iniciar o pareamento. Verifique o código e tente novamente."
        finally:
            self.pairing_loading = False

    async def load_device_detail(self):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        device_id = str(self.router.url.query_parameters.get("id", ""))
        self.selected_device = {}
        self.device_events = []
        self.device_error = ""
        if not device_id.isdigit():
            self.device_error = "Dispositivo não encontrado."
            return
        self.device_loading = True
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meuDispositivo/{device_id}",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            if response.status_code in (401, 403):
                self.auth_token = ""
                self.account_validated = False
                return rx.redirect("/login")
            if response.status_code == 404:
                self.device_error = "A API de dispositivos ainda não está publicada ou este item não existe."
                return
            response.raise_for_status()
            payload = response.json()
            device = payload.get("dispositivo", {}) if isinstance(payload, dict) else {}
            if not isinstance(device, dict) or not device.get("id"):
                raise ValueError("Dispositivo ausente.")
            self.selected_device = {
                "id": str(device.get("id")),
                "name": str(device.get("nome") or device.get("name") or "Armário inteligente"),
                "type": str(device.get("tipo") or device.get("type") or "Dispositivo"),
                "status": self._normalize_device_status(device.get("status")),
                "last_seen": str(device.get("ultimo_contato") or device.get("last_seen") or "Ainda sem leituras"),
            }
            events = payload.get("eventos", [])
            if isinstance(events, list):
                self.device_events = [{
                    "kind": str(event.get("tipo") or event.get("kind") or "Evento"),
                    "value": str(event.get("valor") or event.get("value") or ""),
                    "unit": str(event.get("unidade") or event.get("unit") or ""),
                    "created_at": str(event.get("created_at") or ""),
                } for event in events if isinstance(event, dict)]
        except (httpx.HTTPError, ValueError):
            self.device_error = "Não foi possível carregar os dados do dispositivo."
        finally:
            self.device_loading = False


class ManagementState(AuthState):
    """Read-only management views; Xano enforces the admin role."""

    management_loading: bool = False
    management_error: str = ""
    management_access_denied: bool = False
    management_rows: list[dict[str, str]] = []
    management_metrics: list[dict[str, str]] = [
        {"label": "Pedidos pendentes", "value": "—"},
        {"label": "Vendas no mês", "value": "—"},
        {"label": "Produtos ativos", "value": "—"},
        {"label": "Clientes", "value": "—"},
    ]

    async def _load_admin_resource(self, endpoint: str, section: str):
        if not self.auth_token or not await self._sync_session(str(self.auth_token)):
            return rx.redirect("/login")
        self.management_loading = True
        self.management_error = ""
        self.management_access_denied = False
        self.management_rows = []
        try:
            async with httpx.AsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/{endpoint}",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            if response.status_code in (401, 403):
                self.management_access_denied = response.status_code == 403
                self.management_error = "Esta área exige uma conta administradora." if self.management_access_denied else "Sua sessão expirou. Entre novamente."
                if response.status_code == 401:
                    self.auth_token = ""
                    self.account_validated = False
                    return rx.redirect("/login")
                return
            if response.status_code == 404:
                self.management_error = "A integração de gestão ainda não foi publicada no Xano."
                return
            response.raise_for_status()
            payload = response.json()
            if section == "dashboard":
                data = payload.get("resumo", payload) if isinstance(payload, dict) else {}
                aliases = [
                    ("Pedidos pendentes", "pedidos_pendentes"),
                    ("Vendas no mês", "vendas_mes"),
                    ("Produtos ativos", "produtos_ativos"),
                    ("Clientes", "clientes"),
                ]
                self.management_metrics = [
                    {"label": label, "value": str(data.get(key, "—"))}
                    for label, key in aliases
                ]
            else:
                if isinstance(payload, dict):
                    rows = next((payload.get(key) for key in ("itens", "items", "pedidos", "produtos", "clientes", "relatorios") if isinstance(payload.get(key), list)), [])
                else:
                    rows = payload
                if not isinstance(rows, list):
                    raise ValueError("Formato inesperado na resposta de gestão.")
                self.management_rows = [{
                    "id": str(row.get("id", "")),
                    "name": str(row.get("Nome") or row.get("nome") or row.get("name") or row.get("email") or f"Registro {row.get('id', '')}"),
                    "status": str(row.get("status") or row.get("status_pedido_id") or row.get("status_cliente_id") or "—"),
                    "detail": str(row.get("Total") or row.get("Preco") or row.get("celular") or row.get("created_at") or ""),
                } for row in rows if isinstance(row, dict)]
        except (httpx.HTTPError, ValueError):
            self.management_error = "Não foi possível carregar os dados da gestão. Tente novamente."
        finally:
            self.management_loading = False

    async def load_dashboard(self):
        return await self._load_admin_resource("adminResumo", "dashboard")

    async def load_products(self):
        return await self._load_admin_resource("adminProdutos", "list")

    async def load_orders(self):
        return await self._load_admin_resource("adminPedidos", "list")

    async def load_customers(self):
        return await self._load_admin_resource("adminClientes", "list")

    async def load_reports(self):
        return await self._load_admin_resource("adminRelatorios", "list")


def _label(text: str) -> rx.Component:
    return rx.text(text, as_="label", font_size="0.84rem", font_weight="600", color=INK)

def field(label: str, **props) -> rx.Component:
    return rx.vstack(
        _label(label),
        rx.input(size="3", **INPUT_STYLE, **props),
        spacing="1",
        align_items="stretch",
        width="100%",
    )

def password_field(label: str, placeholder: str, value, on_change, toggle: bool = False) -> rx.Component:
    input_type = rx.cond(AuthState.show_password, "text", "password")
    
    input_element = rx.input(
        placeholder=placeholder,
        value=value,
        on_change=on_change,
        type=input_type,
        size="3",
        **INPUT_STYLE,
    )
    
    if toggle:
        return rx.vstack(
            _label(label),
            rx.hstack(
                input_element,
                rx.button(
                    rx.cond(
                        AuthState.show_password,
                        rx.icon("eye-off", size=18),
                        rx.icon("eye", size=18),
                    ),
                    on_click=AuthState.toggle_password,
                    variant="ghost",
                    cursor="pointer",
                    color=MUTED,
                    width="44px",
                    height="44px",
                    min_width="44px",
                    border_radius="10px",
                    _hover={"background": MUTED_BG, "color": INK},
                    title="Alternar visualização da senha",
                ),
                spacing="2",
                width="100%",
                align="center",
            ),
            spacing="1",
            align_items="stretch",
            width="100%",
        )

    return rx.vstack(
        _label(label),
        input_element,
        spacing="1",
        align_items="stretch",
        width="100%",
    )

def strength_meter() -> rx.Component:
    bars = [
        rx.box(
            height="4px",
            flex="1",
            border_radius="4px",
            background=rx.cond(AuthState.strength >= i, THREAD, "rgba(15,26,51,0.12)"),
            transition="background 0.25s ease",
        )
        for i in range(1, 5)
    ]
    return rx.vstack(
        rx.hstack(*bars, spacing="1", width="100%"),
        rx.text(AuthState.strength_label, font_size="0.76rem", color=MUTED),
        spacing="1",
        align_items="stretch",
        width="100%",
    )

def feedback_box(error: str, success: str) -> rx.Component:
    return rx.fragment(
        rx.cond(
            error != "",
            rx.box(
                rx.hstack(
                    rx.icon("triangle-alert", size=18, color=ERROR),
                    rx.text(error, font_size="0.86rem", font_weight="500", color=ERROR),
                    spacing="2",
                    align="center",
                ),
                padding="10px 14px",
                border_radius="10px",
                background="rgba(180,55,47,0.08)",
                border="1px solid rgba(180,55,47,0.22)",
                width="100%",
            ),
        ),
        rx.cond(
            success != "",
            rx.box(
                rx.hstack(
                    rx.icon("circle-check", size=18, color=OK),
                    rx.text(success, font_size="0.86rem", font_weight="500", color=OK),
                    spacing="2",
                    align="center",
                ),
                padding="10px 14px",
                border_radius="10px",
                background="rgba(47,122,79,0.08)",
                border="1px solid rgba(47,122,79,0.22)",
                width="100%",
            ),
        ),
    )

def stitched_button(label: str, on_click) -> rx.Component:
    return rx.button(
        label,
        on_click=on_click,
        width="100%",
        height="50px",
        border_radius="14px",
        background=INK,
        color=CHALK,
        font_weight="600",
        font_size="0.98rem",
        cursor="pointer",
        outline=f"1.5px dashed {THREAD}",
        outline_offset="-6px",
        transition="all 0.2s ease",
        _hover={"background": DENIM, "transform": "translateY(-1px)"},
        _active={"transform": "translateY(0)"},
    )

def mode_tabs() -> rx.Component:
    is_login = AuthState.active_tab == "login"
    
    return rx.hstack(
        rx.button(
            "Entrar",
            on_click=lambda: AuthState.set_active_tab("login"),
            flex="1",
            text_align="center",
            padding="0.55rem 0",
            border_radius="10px",
            font_weight="600",
            font_size="0.92rem",
            background=rx.cond(is_login, INK, "transparent"),
            color=rx.cond(is_login, CHALK, MUTED),
            cursor="pointer",
            _hover={"color": INK},
            variant="ghost",
        ),
        rx.button(
            "Criar conta",
            on_click=lambda: AuthState.set_active_tab("register"),
            flex="1",
            text_align="center",
            padding="0.55rem 0",
            border_radius="10px",
            font_weight="600",
            font_size="0.92rem",
            background=rx.cond(is_login, "transparent", INK),
            color=rx.cond(is_login, MUTED, CHALK),
            cursor="pointer",
            _hover={"color": INK},
            variant="ghost",
        ),
        padding="4px",
        border_radius="14px",
        background="rgba(15,26,51,0.06)",
        width="100%",
        spacing="0",
    )


# ── Formulários ──────────────────────────────────────────────────────────
def login_form() -> rx.Component:
    return rx.vstack(
        field("E-mail", placeholder="seu.email@exemplo.com", value=AuthState.login_email, on_change=AuthState.set_login_email, type="email"),
        password_field("Senha", "Digite sua senha", AuthState.login_password, AuthState.set_login_password, toggle=True),
        rx.hstack(
            rx.checkbox("Manter conectado", checked=AuthState.remember_me, on_change=AuthState.set_remember_me, color_scheme="amber", size="2"),
            rx.link(
                "Esqueci a senha",
                on_click=AuthState.handle_forgot_password,
                color=INK,
                font_weight="600",
                font_size="0.84rem",
                cursor="pointer",
                _hover={"color": THREAD, "text_decoration": "underline"},
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        rx.cond(
            AuthState.forgot_password_msg != "",
            rx.box(
                rx.text(AuthState.forgot_password_msg, font_size="0.82rem", color=MUTED, line_height="1.5"),
                padding="8px 12px",
                border_radius="8px",
                background=MUTED_BG,
                width="100%",
            ),
        ),
        stitched_button("Entrar no OSDroupa", AuthState.handle_login),
        feedback_box(AuthState.login_error, AuthState.login_success),
        spacing="3",
        width="100%",
    )

def register_form() -> rx.Component:
    return rx.vstack(
        field("Nome completo", placeholder="Maria Silva Souza", value=AuthState.full_name, on_change=AuthState.set_full_name),
        field("E-mail pessoal ou comercial", placeholder="voce@exemplo.com", value=AuthState.register_email, on_change=AuthState.set_register_email, type="email"),
        field("Celular / WhatsApp", placeholder="(11) 98765-4321", value=AuthState.phone, on_change=AuthState.set_phone, type="tel"),
        password_field("Senha de acesso", "Mínimo de 8 caracteres", AuthState.register_password, AuthState.set_register_password, toggle=True),
        strength_meter(),
        password_field("Confirmar senha", "Repita a senha criada", AuthState.confirm_password, AuthState.set_confirm_password),
        rx.checkbox(
            "Concordo com os Termos de Uso e Política de Privacidade do OSDroupa",
            checked=AuthState.accepted_terms,
            on_change=AuthState.set_accepted_terms,
            color_scheme="amber",
            size="2",
        ),
        stitched_button("Criar minha conta", AuthState.handle_register),
        feedback_box(AuthState.register_error, AuthState.register_success),
        spacing="3",
        width="100%",
    )


# ── Painéis Principais (Brand Panel & Form Panel) ─────────────────────────
def _feature_pill(icon_name: str, title: str, subtitle: str) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon(icon_name, size=20, color=THREAD),
            padding="10px",
            border_radius="12px",
            background="rgba(233,162,59,0.12)",
        ),
        rx.vstack(
            rx.text(title, font_weight="700", font_size="0.88rem", color=CHALK),
            rx.text(subtitle, font_size="0.78rem", color="#A4B3D4", line_height="1.4"),
            spacing="0",
            align_items="flex-start",
        ),
        spacing="3",
        align="center",
        width="100%",
    )

def brand_panel() -> rx.Component:
    return rx.vstack(
        # Topo com Logotipo
        rx.hstack(
            rx.html(LOGO_SVG),
            rx.text("OSDROUPA", font_family=DISPLAY, font_weight="700", font_size="1.35rem", letter_spacing="0.14em", color=CHALK),
            align="center",
            spacing="3",
        ),
        # Chamada Principal
        rx.vstack(
            rx.heading(
                "Abra o armário já sabendo o que vestir.",
                font_family=DISPLAY,
                font_weight="700",
                font_size=["1.85rem", "2.3rem", "2.8rem"],
                line_height="1.08",
                letter_spacing="-0.02em",
                color=CHALK,
                max_width="16ch",
            ),
            rx.text(
                "O OSDroupa cruza a previsão climática, seus compromissos e as roupas do seu acervo para montar o look inteligente de cada dia.",
                color="#C9D3E8",
                font_size="0.98rem",
                line_height="1.6",
                max_width="44ch",
            ),
            spacing="3",
            align_items="flex-start",
        ),
        # Ilustração Arara de Roupas
        rx.box(
            rx.html(RAIL_SVG),
            width="100%",
            max_width="520px",
            margin_y="0.2rem",
        ),
        # Destaques Tecnológicos
        rx.vstack(
            _feature_pill("sparkles", "Look do Dia com IA", "Sugestões personalizadas por ocasião e clima local."),
            _feature_pill("tag", "Arara Conectada (IoT)", "Rastreamento por RFID e LEDs Pick-to-Light para localização imediata."),
            _feature_pill("leaf", "Moda Consciente", "Maximize o uso de cada peça e apoie a confecção sob demanda."),
            spacing="3",
            width="100%",
        ),
        justify="between",
        align_items="flex-start",
        spacing="5",
        height="100%",
        padding=["1.6rem", "2.2rem", "2.8rem"],
        background_color=INK,
        background_image=(
            "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),"
            "linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)"
        ),
        background_size="28px 28px",
    )

def form_panel() -> rx.Component:
    is_login = AuthState.active_tab == "login"
    
    return rx.center(
        rx.vstack(
            # Alternador de Abas
            mode_tabs(),
            
            # Container do Formulário
            rx.vstack(
                rx.heading(
                    rx.cond(is_login, "Que bom ver você de novo.", "Monte seu guarda-roupa."),
                    font_family=DISPLAY,
                    font_weight="700",
                    font_size=["1.65rem", "1.85rem", "2.05rem"],
                    letter_spacing="-0.02em",
                    color=INK,
                    line_height="1.15",
                ),
                rx.text(
                    rx.cond(
                        is_login,
                        "Entre para acessar as peças e recomendações do dia.",
                        "Leva menos de 1 minuto. Cadastre-se para conectar sua arara.",
                    ),
                    color=MUTED,
                    font_size="0.92rem",
                    line_height="1.5",
                ),
                rx.cond(
                    is_login,
                    login_form(),
                    register_form(),
                ),
                spacing="4",
                align_items="flex-start",
                width="100%",
                padding=["1.2rem", "1.6rem", "2rem"],
                background="#FFFFFF",
                border="1px solid rgba(15,26,51,0.1)",
                border_radius="22px",
                box_shadow="0 10px 30px rgba(15,26,51,0.04)",
            ),
            spacing="4",
            width="100%",
            max_width="450px",
        ),
        background=CHALK,
        padding=["1.5rem", "2rem", "2.8rem"],
        width="100%",
    )


# ── Componentes da Home Page (Squadeasy + WeAreOSM inspired) ──────────────
def public_account_actions() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        rx.hstack(
            rx.link(
                rx.button("Meu armário", variant="ghost", color=CHALK, font_weight="600"),
                href="/armario",
            ),
            rx.link(
                rx.button("Meu perfil", background=THREAD, color=INK, font_weight="700", border_radius="100px"),
                href="/perfil",
            ),
            spacing="2",
            align_items="center",
        ),
        rx.hstack(
            rx.link(
                rx.button(
                    "Entrar",
                    variant="ghost",
                    color=CHALK,
                    font_weight="600",
                    font_size="0.9rem",
                    cursor="pointer",
                    _hover={"background": "rgba(255,255,255,0.08)"},
                ),
                href="/login",
            ),
            rx.link(
                rx.button(
                    rx.hstack(
                        rx.text("Criar Conta"),
                        rx.icon("arrow-up-right", size=16),
                        spacing="1",
                        align_items="center",
                    ),
                    background=THREAD,
                    color=INK,
                    font_weight="700",
                    font_size="0.9rem",
                    border_radius="100px",
                    padding_x="1.4rem",
                    height="42px",
                    box_shadow="0 4px 18px rgba(233,162,59,0.35)",
                    cursor="pointer",
                    _hover={"transform": "translateY(-1px)", "box_shadow": "0 6px 24px rgba(233,162,59,0.5)"},
                ),
                href="/cadastro",
            ),
            spacing="3",
            align_items="center",
        ),
    )


def home_navbar() -> rx.Component:
    """Navbar minimalista e moderna com logo, links de seção e CTA de entrada."""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.html(LOGO_SVG),
                rx.vstack(
                    rx.text(
                        "OSDROUPA",
                        font_family=DISPLAY,
                        font_weight="800",
                        font_size="1.25rem",
                        color=CHALK,
                        letter_spacing="0.08em",
                    ),
                    rx.text(
                        "MODA INTELIGENTE & IOT",
                        font_size="0.65rem",
                        font_weight="700",
                        color=THREAD,
                        letter_spacing="0.16em",
                    ),
                    spacing="0",
                    align_items="flex-start",
                ),
                spacing="3",
                align_items="center",
            ),
            rx.spacer(),
            # Menu de navegação desktop
            rx.hstack(
                rx.link(
                    "Loja",
                    href="/loja",
                    color="rgba(248,249,250,0.8)",
                    font_size="0.9rem",
                    font_weight="600",
                    _hover={"color": THREAD},
                ),
                rx.link(
                    "O Armário",
                    href="#recursos",
                    color="rgba(248,249,250,0.8)",
                    font_size="0.9rem",
                    font_weight="500",
                    _hover={"color": THREAD},
                ),
                rx.link(
                    "Como Funciona",
                    href="#como-funciona",
                    color="rgba(248,249,250,0.8)",
                    font_size="0.9rem",
                    font_weight="500",
                    _hover={"color": THREAD},
                ),
                rx.link(
                    "Serviços & Alfaiataria",
                    href="#servicos",
                    color="rgba(248,249,250,0.8)",
                    font_size="0.9rem",
                    font_weight="500",
                    _hover={"color": THREAD},
                ),
                rx.link(
                    "Depoimentos",
                    href="#depoimentos",
                    color="rgba(248,249,250,0.8)",
                    font_size="0.9rem",
                    font_weight="500",
                    _hover={"color": THREAD},
                ),
                spacing="5",
                display=["none", "none", "flex"],
            ),
            rx.spacer(),
            public_account_actions(),
            width="100%",
            max_width="1220px",
            margin_x="auto",
            align_items="center",
        ),
        padding_y="1rem",
        padding_x=["1.2rem", "2rem"],
        background="rgba(15,26,51,0.88)",
        backdrop_filter="blur(20px)",
        border_bottom="1px solid rgba(255,255,255,0.08)",
        position="sticky",
        top="0",
        z_index="100",
        width="100%",
    )


def home_hero_section() -> rx.Component:
    """Hero section com tipografia bold e marcadores de destaque estilo Squadeasy/WeAreOSM."""
    return rx.box(
        rx.vstack(
            # Badge de boas-vindas / definição estilo WeAreOSM
            rx.hstack(
                rx.box(
                    rx.text("✨ CONECTADO", font_size="0.72rem", font_weight="800", color=THREAD, letter_spacing="0.12em"),
                    background="rgba(233,162,59,0.15)",
                    border="1px solid rgba(233,162,59,0.35)",
                    border_radius="100px",
                    padding_x="0.8rem",
                    padding_y="0.3rem",
                ),
                rx.text(
                    "O guarda-roupa que pensa no seu próximo look antes de você",
                    color="rgba(248,249,250,0.75)",
                    font_size="0.86rem",
                    font_weight="500",
                ),
                spacing="2",
                align_items="center",
                padding_x="0.5rem",
                padding_y="0.3rem",
                background="rgba(255,255,255,0.04)",
                border_radius="100px",
                border="1px solid rgba(255,255,255,0.08)",
            ),

            # Título marcante de impacto (Squadeasy bold + WeAreOSM punch)
            rx.vstack(
                rx.heading(
                    "Abra seu armário.",
                    font_family=DISPLAY,
                    font_weight="800",
                    font_size=["2.6rem", "3.6rem", "4.8rem"],
                    line_height="1.02",
                    letter_spacing="-0.03em",
                    color=CHALK,
                    text_align="center",
                ),
                rx.heading(
                    "Vista a sua melhor versão.",
                    font_family=DISPLAY,
                    font_weight="800",
                    font_size=["2.6rem", "3.6rem", "4.8rem"],
                    line_height="1.02",
                    letter_spacing="-0.03em",
                    background=f"linear-gradient(90deg, #FFFFFF 0%, {THREAD} 100%)",
                    background_clip="text",
                    text_fill_color="transparent",
                    text_align="center",
                ),
                spacing="1",
                align_items="center",
                margin_top="1rem",
            ),

            # Subtítulo explicativo
            rx.text(
                "O OsDRoupa combina previsão do tempo em tempo real, sua agenda do dia e a "
                "inteligência do seu acervo têxtil para que você nunca mais perca tempo pensando no que vestir.",
                color="rgba(248,249,250,0.75)",
                font_size=["1rem", "1.15rem"],
                text_align="center",
                max_width="660px",
                line_height="1.6",
                margin_top="0.5rem",
            ),

            # CTAs principais
            rx.hstack(
                rx.link(
                    rx.button(
                        rx.hstack(
                            rx.text("Começar Agora Grátis"),
                            rx.icon("sparkles", size=18),
                            spacing="2",
                            align_items="center",
                        ),
                        background=THREAD,
                        color=INK,
                        font_size="1rem",
                        font_weight="700",
                        height="52px",
                        padding_x="2rem",
                        border_radius="100px",
                        box_shadow="0 8px 30px rgba(233,162,59,0.45)",
                        cursor="pointer",
                        _hover={"transform": "translateY(-2px)", "box_shadow": "0 12px 36px rgba(233,162,59,0.6)"},
                    ),
                    href="/cadastro",
                ),
                rx.link(
                    rx.button(
                        rx.hstack(
                            rx.icon("circle-play", size=18),
                            rx.text("Ver Demonstração"),
                            spacing="2",
                            align_items="center",
                        ),
                        background="rgba(255,255,255,0.06)",
                        color=CHALK,
                        border="1px solid rgba(255,255,255,0.18)",
                        font_size="1rem",
                        font_weight="600",
                        height="52px",
                        padding_x="1.8rem",
                        border_radius="100px",
                        cursor="pointer",
                        _hover={"background": "rgba(255,255,255,0.12)"},
                    ),
                    href="#como-funciona",
                ),
                spacing="4",
                align_items="center",
                margin_top="1.2rem",
                wrap="wrap",
                justify="center",
            ),

            # Card Flutuante / Arara Interativa SVG com Tag Inteligente
            rx.box(
                rx.box(
                    rx.html(RAIL_SVG),
                    width="100%",
                    max_width="680px",
                    margin_x="auto",
                ),
                padding=["1rem", "2rem"],
                margin_top="2.5rem",
                background="rgba(255,255,255,0.03)",
                border="1px solid rgba(255,255,255,0.1)",
                border_radius="28px",
                box_shadow="0 25px 80px rgba(0,0,0,0.5)",
                width="100%",
                max_width="740px",
            ),
            spacing="4",
            align_items="center",
            width="100%",
            max_width="920px",
            margin_x="auto",
        ),
        padding_y=["3rem", "5rem"],
        padding_x=["1.2rem", "2rem"],
        width="100%",
    )


def home_marquee_strip() -> rx.Component:
    """Faixa horizontal animada contínua de métricas e badges estilo Squadeasy/WeAreOSM."""
    items = [
        "🧥 +15.000 Looks Sugeridos",
        "⚡ Algoritmo Climático 22°C/Chuva",
        "🎯 RFID & LED Pick-to-Light",
        "🌱 Moda Circular & Zero Desperdício",
        "📍 Entrega com Validação de CEP",
        "🧵 Alfaiataria sob Demanda",
    ]
    pills = [
        rx.box(
            rx.text(item, font_size="0.88rem", font_weight="700", color=CHALK),
            padding_x="1.4rem",
            padding_y="0.6rem",
            background="rgba(255,255,255,0.06)",
            border="1px solid rgba(255,255,255,0.1)",
            border_radius="100px",
            margin_right="1rem",
            white_space="nowrap",
        )
        for item in (items * 2)
    ]
    return rx.box(
        rx.box(
            rx.hstack(*pills, spacing="2"),
            class_name="osd-marquee",
        ),
        overflow="hidden",
        width="100%",
        padding_y="1.2rem",
        border_top="1px solid rgba(255,255,255,0.08)",
        border_bottom="1px solid rgba(255,255,255,0.08)",
        background="rgba(0,0,0,0.25)",
    )


def home_features_section() -> rx.Component:
    """Grid de pilares inteligentes estilo Squadeasy e OSM."""
    features = [
        {
            "icon": "sparkles",
            "tag": "INTELIGÊNCIA ARTIFICIAL",
            "title": "Look do Dia sob Medida",
            "desc": "Conexão direta com a meteorologia local e a sua agenda Google/Outlook para harmonizar estilo, temperatura e formalidade.",
            "color": "#E9A23B",
        },
        {
            "icon": "radio",
            "tag": "IOT & PICK-TO-LIGHT",
            "title": "Arara Conectada",
            "desc": "Sensores RFID e anéis de LED em cada cabide. O app acende a luz exata da peça na sua arara física instantaneamente.",
            "color": "#64B5F6",
        },
        {
            "icon": "map-pin",
            "tag": "LOGÍSTICA PRECISA",
            "title": "Entrega por CEP Validado",
            "desc": "Integração automática com o ViaCEP e geolocalização do Xano para entrega rápida e segura das suas roupas higienizadas.",
            "color": "#81C784",
        },
        {
            "icon": "scissors",
            "tag": "ALFAIATARIA MODERNA",
            "title": "Ajuste Fino Sob Medida",
            "desc": "Costureiros parceiros e oficinas qualificadas para pequenos reparos, bainhas e transformações de peças do seu guarda-roupa.",
            "color": "#FFB74D",
        },
        {
            "icon": "leaf",
            "tag": "SUSTENTABILIDADE REAL",
            "title": "Ciclo de Roupa Viva",
            "desc": "Descubra peças esquecidas no fundo do armário e reduza a compra por impulso aproveitando 100% do que você já possui.",
            "color": "#4DB6AC",
        },
        {
            "icon": "shield-check",
            "tag": "SEGURANÇA & DADOS",
            "title": "Segurança de Ponta a Ponta",
            "desc": "Autenticação criptografada em nuvem, controle rigoroso de privacidade e painel exclusivo para o cliente.",
            "color": "#BA68C8",
        },
    ]

    cards = [
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon(f["icon"], size=22, color=f["color"]),
                        background="rgba(255,255,255,0.06)",
                        padding="0.8rem",
                        border_radius="14px",
                        border=f"1px solid {f['color']}33",
                    ),
                    rx.spacer(),
                    rx.text(f["tag"], font_size="0.68rem", font_weight="800", color=f["color"], letter_spacing="0.1em"),
                    width="100%",
                    align_items="center",
                ),
                rx.heading(
                    f["title"],
                    font_family=DISPLAY,
                    font_size="1.35rem",
                    font_weight="700",
                    color=CHALK,
                    margin_top="0.5rem",
                ),
                rx.text(
                    f["desc"],
                    color="rgba(248,249,250,0.7)",
                    font_size="0.92rem",
                    line_height="1.55",
                ),
                spacing="2",
                align_items="flex-start",
            ),
            background="rgba(255,255,255,0.03)",
            border="1px solid rgba(255,255,255,0.08)",
            border_radius="22px",
            padding="1.8rem",
            box_shadow="0 10px 30px rgba(0,0,0,0.2)",
            _hover={
                "border": f"1px solid {f['color']}66",
                "transform": "translateY(-4px)",
                "box_shadow": f"0 16px 40px rgba(0,0,0,0.4)",
            },
            transition="all 0.25s ease",
        )
        for f in features
    ]

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.text("⚙️ CAPACIDADES", font_size="0.75rem", font_weight="800", color=THREAD, letter_spacing="0.12em"),
                    background="rgba(233,162,59,0.15)",
                    border="1px solid rgba(233,162,59,0.3)",
                    border_radius="100px",
                    padding_x="0.8rem",
                    padding_y="0.3rem",
                ),
            ),
            rx.heading(
                "Tecnologia invisível.",
                font_family=DISPLAY,
                font_weight="800",
                font_size=["2rem", "2.8rem"],
                color=CHALK,
                letter_spacing="-0.02em",
                text_align="center",
            ),
            rx.heading(
                "Estilo impecável todos os dias.",
                font_family=DISPLAY,
                font_weight="800",
                font_size=["2rem", "2.8rem"],
                background=f"linear-gradient(90deg, #FFFFFF 0%, {THREAD} 100%)",
                background_clip="text",
                text_fill_color="transparent",
                letter_spacing="-0.02em",
                text_align="center",
            ),
            rx.text(
                "Inspirado na precisão de software e na alfaiataria de corte fino.",
                color=MUTED,
                font_size="1rem",
                text_align="center",
                margin_bottom="2rem",
            ),
            rx.grid(
                *cards,
                columns={"initial": "1", "sm": "2", "md": "3"},
                spacing="5",
                width="100%",
            ),
            spacing="3",
            align_items="center",
            width="100%",
            max_width="1220px",
            margin_x="auto",
        ),
        id="recursos",
        padding_y=["4rem", "6rem"],
        padding_x=["1.2rem", "2rem"],
        width="100%",
    )


def home_osm_definition_block() -> rx.Component:
    """Bloco icônico de definição bem-humorada e institucional inspirado na WeAreOSM."""
    return rx.box(
        rx.vstack(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text("📖 DEFINIÇÃO", font_size="0.72rem", font_weight="800", color=THREAD, letter_spacing="0.14em"),
                        rx.spacer(),
                        rx.badge("Verificado", color_scheme="amber", size="2"),
                        width="100%",
                        align_items="center",
                    ),
                    rx.heading(
                        "OsDRoupa /ˈos-de-how-pah/",
                        font_family=DISPLAY,
                        font_size=["1.8rem", "2.4rem"],
                        font_weight="800",
                        color=CHALK,
                        letter_spacing="-0.02em",
                    ),
                    rx.text(
                        "[substantivo masculino — a fusão definitiva entre o guarda-roupa físico e o cérebro digital]",
                        color=THREAD,
                        font_style="italic",
                        font_size="0.95rem",
                    ),
                    rx.text(
                        "“A vida é curta demais para perder 15 minutos em frente a um armário lotado dizendo "
                        "‘eu não tenho nada para vestir’.” — Manifesto OsDRoupa",
                        color="rgba(248,249,250,0.85)",
                        font_size="1.05rem",
                        line_height="1.6",
                        margin_top="0.6rem",
                    ),
                    spacing="3",
                    align_items="flex-start",
                ),
                padding=["1.8rem", "2.5rem"],
                background="linear-gradient(135deg, rgba(31,53,96,0.5) 0%, rgba(15,26,51,0.9) 100%)",
                border="1px solid rgba(233,162,59,0.3)",
                border_radius="24px",
                box_shadow="0 20px 60px rgba(0,0,0,0.35)",
                width="100%",
                max_width="980px",
            ),
            width="100%",
            align_items="center",
        ),
        id="como-funciona",
        padding_y=["2rem", "4rem"],
        padding_x=["1.2rem", "2rem"],
        width="100%",
    )


def home_numbers_banner() -> rx.Component:
    """Banner de números expressivos com cards estilo Squadeasy."""
    stats = [
        {"num": "15.000+", "label": "Looks sugeridos com IA", "sub": "98% de assertividade climática"},
        {"num": "100%", "label": "Rastreio por CEP", "sub": "Validação automática via ViaCEP"},
        {"num": "4.9 ★", "label": "Satisfação dos usuários", "sub": "Mais tempo livre pela manhã"},
        {"num": "30%", "label": "Menos roupas ociosas", "sub": "Economia circular e consciente"},
    ]
    stat_boxes = [
        rx.vstack(
            rx.heading(
                s["num"],
                font_family=DISPLAY,
                font_size=["2.2rem", "3rem"],
                font_weight="800",
                color=THREAD,
                letter_spacing="-0.03em",
            ),
            rx.text(s["label"], font_weight="700", font_size="1rem", color=CHALK),
            rx.text(s["sub"], font_size="0.82rem", color=MUTED),
            spacing="1",
            align_items="flex-start",
            padding="1.8rem",
            background="rgba(255,255,255,0.03)",
            border="1px solid rgba(255,255,255,0.08)",
            border_radius="20px",
            width="100%",
        )
        for s in stats
    ]
    return rx.box(
        rx.vstack(
            rx.grid(
                *stat_boxes,
                columns={"initial": "1", "sm": "2", "md": "4"},
                spacing="4",
                width="100%",
            ),
            width="100%",
            max_width="1220px",
            margin_x="auto",
        ),
        id="depoimentos",
        padding_y=["3rem", "4rem"],
        padding_x=["1.2rem", "2rem"],
        width="100%",
    )


def home_cta_banner() -> rx.Component:
    """Banner final de conversão estilo Squadeasy/WeAreOSM."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.heading(
                    "Pronto para simplificar suas manhãs?",
                    font_family=DISPLAY,
                    font_weight="800",
                    font_size=["2rem", "3rem"],
                    color=INK,
                    letter_spacing="-0.02em",
                    text_align="center",
                ),
                rx.text(
                    "Cadastre-se hoje mesmo e experimente o poder do armário inteligente com IA e entrega por CEP.",
                    color=INK,
                    font_size="1.05rem",
                    text_align="center",
                    max_width="540px",
                    opacity=0.85,
                ),
                rx.hstack(
                    rx.link(
                        rx.button(
                            "Criar Minha Conta Grátis",
                            background=INK,
                            color=CHALK,
                            font_weight="700",
                            font_size="1rem",
                            height="50px",
                            padding_x="2rem",
                            border_radius="100px",
                            cursor="pointer",
                            _hover={"background": DENIM},
                        ),
                        href="/cadastro",
                    ),
                    rx.link(
                        rx.button(
                            "Já sou cliente • Entrar",
                            variant="outline",
                            color=INK,
                            border_color=INK,
                            font_weight="700",
                            font_size="1rem",
                            height="50px",
                            padding_x="1.8rem",
                            border_radius="100px",
                            cursor="pointer",
                            _hover={"background": "rgba(15,26,51,0.06)"},
                        ),
                        href="/login",
                    ),
                    spacing="3",
                    align_items="center",
                    wrap="wrap",
                    justify="center",
                    margin_top="1rem",
                ),
                spacing="3",
                align_items="center",
            ),
            background=f"linear-gradient(135deg, {THREAD} 0%, #F5C26B 100%)",
            border_radius="32px",
            padding=["2.5rem 1.5rem", "4rem 3rem"],
            box_shadow="0 25px 60px rgba(233,162,59,0.3)",
            width="100%",
            max_width="1140px",
            margin_x="auto",
        ),
        id="servicos",
        padding_y=["3rem", "5rem"],
        padding_x=["1.2rem", "2rem"],
        width="100%",
    )


def home_footer() -> rx.Component:
    """Rodapé limpo e elegante inspirado nas duas referências."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.html(LOGO_SVG),
                    rx.vstack(
                        rx.text("OSDROUPA", font_family=DISPLAY, font_weight="800", font_size="1.2rem", color=CHALK),
                        rx.text("Inteligência Têxtil & IoT", font_size="0.75rem", color=MUTED),
                        spacing="0",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.link("Início", href="/", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Entrar", href="/login", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Criar Conta", href="/cadastro", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Meus Endereços", href="/enderecos", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    spacing="4",
                ),
                width="100%",
                align_items="center",
                wrap="wrap",
            ),
            rx.divider(color_scheme="gray", opacity=0.15, margin_y="1.5rem"),
            rx.hstack(
                rx.text(
                    "© 2026 OsDRoupa. Todos os direitos reservados. Design inspirado em Squadeasy & WeAreOSM.",
                    color=MUTED,
                    font_size="0.8rem",
                ),
                rx.spacer(),
                rx.text("Feito com Reflex + Xano no Brasil 🇧🇷", color=MUTED, font_size="0.8rem"),
                width="100%",
                align_items="center",
                wrap="wrap",
            ),
            spacing="2",
            width="100%",
            max_width="1220px",
            margin_x="auto",
        ),
        padding_y="2.5rem",
        padding_x=["1.2rem", "2rem"],
        background="#0A1122",
        border_top="1px solid rgba(255,255,255,0.06)",
        width="100%",
    )


def landing_home() -> rx.Component:
    """Home page principal completa inspirada em Squadeasy e WeAreOSM."""
    return rx.box(
        rx.el.style(CSS),
        home_navbar(),
        home_hero_section(),
        home_marquee_strip(),
        home_features_section(),
        home_osm_definition_block(),
        home_numbers_banner(),
        home_cta_banner(),
        home_footer(),
        min_height="100vh",
        background=f"linear-gradient(180deg, {INK} 0%, {DENIM} 40%, {INK} 100%)",
        font_family=BODY,
        width="100%",
    )


# ── Shell Autenticação & Páginas ─────────────────────────────────────────
def auth_shell(default_tab: str = "login") -> rx.Component:
    return rx.box(
        rx.el.style(CSS),
        rx.box(
            brand_panel(),
            form_panel(),
            display="grid",
            grid_template_columns=["1fr", "1fr", "1.15fr 0.85fr"],
            width="100%",
            max_width="1180px",
            border_radius="28px",
            overflow="hidden",
            box_shadow="0 35px 90px rgba(0,0,0,0.45)",
            background=INK,
        ),
        display="flex",
        align_items="center",
        justify_content="center",
        min_height="100vh",
        padding=["0.75rem", "1.25rem", "2rem"],
        background=f"linear-gradient(155deg, {DENIM} 0%, {INK} 75%)",
        font_family=BODY,
        on_mount=lambda: AuthState.set_active_tab(default_tab),
    )

def index() -> rx.Component:
    return landing_home()

def login_page() -> rx.Component:
    return auth_shell(default_tab="login")

def signup_page() -> rx.Component:
    return auth_shell(default_tab="register")


# ── Dashboard (Painel do Usuário Pós-Autenticação) ────────────────────────
def _address_form() -> rx.Component:
    """Formulário de cadastro/edição de endereço com autopreenchimento por CEP."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading(
                    rx.cond(AddressState.editing_id > 0, "Editar Endereço", "Novo Endereço"),
                    font_size="1.1rem", font_family=DISPLAY, color=INK,
                ),
                rx.spacer(),
                rx.icon_button(
                    rx.icon("x"),
                    on_click=AddressState.toggle_form,
                    variant="ghost", size="2",
                    aria_label="Fechar formulário",
                ),
                width="100%",
                align_items="center",
            ),
            rx.divider(color_scheme="gray"),

            # ── CEP com botão buscar ──────────────────────────────────────
            rx.vstack(
                _label("CEP *"),
                rx.hstack(
                    rx.input(
                        placeholder="00000-000",
                        value=AddressState.form_cep,
                        on_change=AddressState.set_form_cep,
                        max_length=9,
                        id="input-cep",
                        **INPUT_STYLE,
                    ),
                    rx.button(
                        rx.cond(
                            AddressState.cep_loading,
                            rx.spinner(size="2"),
                            rx.text("Buscar"),
                        ),
                        on_click=AddressState.buscar_cep,
                        loading=AddressState.cep_loading,
                        background=DENIM,
                        color="white",
                        border_radius="12px",
                        height="46px",
                        padding_x="1.2rem",
                        font_weight="600",
                        _hover={"background": INK},
                        id="btn-buscar-cep",
                    ),
                    width="100%",
                    spacing="2",
                ),
                rx.cond(
                    AddressState.cep_error != "",
                    rx.text(AddressState.cep_error, color=ERROR, font_size="0.82rem"),
                ),
                spacing="1",
                align_items="stretch",
                width="100%",
            ),

            # ── Logradouro + Número ───────────────────────────────────────
            rx.flex(
                rx.vstack(
                    _label("Logradouro *"),
                    rx.input(
                        placeholder="Rua, Avenida…",
                        value=AddressState.form_logradouro,
                        on_change=AddressState.set_form_logradouro,
                        id="input-logradouro",
                        **INPUT_STYLE,
                    ),
                    spacing="1", align_items="stretch", width="100%",
                ),
                rx.vstack(
                    _label("Número *"),
                    rx.input(
                        placeholder="123",
                        value=AddressState.form_numero,
                        on_change=AddressState.set_form_numero,
                        id="input-numero",
                        **{**INPUT_STYLE, "width": "110px"},
                    ),
                    spacing="1", align_items="stretch",
                ),
                direction={"initial": "column", "sm": "row"},
                spacing="3",
                width="100%",
            ),

            # ── Complemento + Bairro ──────────────────────────────────────
            rx.flex(
                rx.vstack(
                    _label("Complemento"),
                    rx.input(
                        placeholder="Apto, Sala…",
                        value=AddressState.form_complemento,
                        on_change=AddressState.set_form_complemento,
                        id="input-complemento",
                        **INPUT_STYLE,
                    ),
                    spacing="1", align_items="stretch", width="100%",
                ),
                rx.vstack(
                    _label("Bairro"),
                    rx.input(
                        placeholder="Bairro",
                        value=AddressState.form_bairro,
                        on_change=AddressState.set_form_bairro,
                        id="input-bairro",
                        **INPUT_STYLE,
                    ),
                    spacing="1", align_items="stretch", width="100%",
                ),
                direction={"initial": "column", "sm": "row"},
                spacing="3",
                width="100%",
            ),

            # ── Cidade (readonly) + UF (readonly) ─────────────────────────
            rx.flex(
                rx.vstack(
                    _label("Cidade"),
                    rx.input(
                        placeholder="Preenchido pelo CEP",
                        value=AddressState.form_cidade,
                        read_only=True,
                        id="input-cidade",
                        **{**INPUT_STYLE, "background": "#F0F2F5", "cursor": "not-allowed"},
                    ),
                    spacing="1", align_items="stretch", width="100%",
                ),
                rx.vstack(
                    _label("UF"),
                    rx.input(
                        placeholder="UF",
                        value=AddressState.form_uf,
                        read_only=True,
                        id="input-uf",
                        **{**INPUT_STYLE, "width": "80px", "background": "#F0F2F5", "cursor": "not-allowed"},
                    ),
                    spacing="1", align_items="stretch",
                ),
                direction={"initial": "column", "sm": "row"},
                spacing="3",
                width="100%",
            ),

            # ── Referência + Padrão ───────────────────────────────────────
            rx.vstack(
                _label("Referência (opcional)"),
                rx.input(
                    placeholder="Ex: Próximo ao MASP",
                    value=AddressState.form_referencia,
                    on_change=AddressState.set_form_referencia,
                    id="input-referencia",
                    **INPUT_STYLE,
                ),
                spacing="1", align_items="stretch", width="100%",
            ),
            rx.hstack(
                rx.checkbox(
                    "Definir como endereço padrão de entrega",
                    checked=AddressState.form_padrao,
                    on_change=AddressState.set_form_padrao,
                    color_scheme="amber",
                    id="chk-padrao",
                ),
                width="100%",
            ),

            # ── Feedback + Botão Salvar ───────────────────────────────────
            rx.cond(
                AddressState.address_error != "",
                rx.callout.root(
                    rx.callout.icon(rx.icon("triangle-alert")),
                    rx.callout.text(AddressState.address_error),
                    color="red", variant="soft",
                ),
            ),
            rx.button(
                rx.cond(
                    AddressState.address_loading,
                    rx.hstack(rx.spinner(size="2"), rx.text("Salvando…"), spacing="2"),
                    rx.cond(
                        AddressState.editing_id > 0,
                        rx.text("Atualizar Endereço"),
                        rx.text("Salvar Endereço"),
                    ),
                ),
                on_click=AddressState.salvar_endereco,
                loading=AddressState.address_loading,
                background=THREAD,
                color=INK,
                border_radius="12px",
                height="46px",
                width="100%",
                font_weight="700",
                _hover={"background": "#d48e2a"},
                id="btn-salvar-endereco",
            ),
            spacing="4",
            width="100%",
        ),
        background="#FFFFFF",
        border="1px solid rgba(15,26,51,0.12)",
        border_radius="20px",
        padding="1.8rem",
        box_shadow="0 8px 32px rgba(15,26,51,0.06)",
        width="100%",
    )


def _address_card(addr: dict) -> rx.Component:
    """Cartão de endereço salvo com ação de marcar padrão / editar."""
    cep_info = addr["_cep"]
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    # Logradouro + Número como filhos separados do rx.text
                    rx.text(
                        addr["logradouro"], ", ", addr["numero"],
                        font_weight="700",
                        font_size="1rem",
                        color=INK,
                    ),
                    rx.text(
                        addr["bairro"], " — ", cep_info["cidade"], "/", cep_info["uf"],
                        font_size="0.85rem",
                        color=MUTED,
                    ),
                    rx.text(
                        "CEP ", cep_info["cep"],
                        font_size="0.82rem",
                        color=MUTED,
                    ),
                    spacing="0",
                    align_items="flex-start",
                ),
                rx.spacer(),
                rx.vstack(
                    rx.cond(
                        addr["padrao"],
                        rx.badge("Padrão", color_scheme="amber", size="2"),
                        rx.button(
                            "Tornar padrão",
                            on_click=AddressState.marcar_padrao(addr["id"]),
                            size="1",
                            variant="outline",
                            color_scheme="gray",
                            border_radius="8px",
                        ),
                    ),
                    rx.button(
                        rx.icon("pencil", size=14),
                        on_click=AddressState.editar_endereco(addr),
                        size="1",
                        variant="ghost",
                        color_scheme="blue",
                    ),
                    spacing="2",
                    align_items="flex-end",
                ),
                width="100%",
                align_items="flex-start",
            ),
            rx.cond(
                addr["complemento"] != "",
                rx.text(
                    "Complemento: ", addr["complemento"],
                    font_size="0.82rem", color=MUTED,
                ),
            ),
            rx.cond(
                addr["referencia"] != "",
                rx.text(
                    "Ref: ", addr["referencia"],
                    font_size="0.82rem", color=MUTED, font_style="italic",
                ),
            ),
            spacing="2",
            width="100%",
        ),
        background=rx.cond(addr["padrao"], "rgba(233,162,59,0.06)", "#FFFFFF"),
        border=rx.cond(
            addr["padrao"],
            "1.5px solid rgba(233,162,59,0.5)",
            "1px solid rgba(15,26,51,0.08)",
        ),
        border_radius="16px",
        padding="1.4rem",
        box_shadow="0 4px 16px rgba(15,26,51,0.04)",
        width="100%",
    )


def enderecos_page() -> rx.Component:
    return rx.box(
        rx.cond(AuthState.account_validated, _enderecos_content(), auth_loading_screen()),
        min_height="100vh",
    )


def _enderecos_content() -> rx.Component:
    """Página de gerenciamento de endereços do cliente (Change 003)."""
    return rx.box(
        # ── Navbar ──────────────────────────────────────────────────────
        rx.box(
            rx.hstack(
                rx.hstack(
                    rx.html(LOGO_SVG),
                    rx.heading(
                        "OSDROUPA",
                        font_family=DISPLAY,
                        font_size="1.3rem",
                        color="#F8F9FA",
                        letter_spacing="0.06em",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.link(
                        rx.text("Loja", font_size="0.9rem", color="rgba(248,249,250,0.7)", _hover={"color": "#F8F9FA"}),
                        href="/loja",
                    ),
                    rx.link(
                        rx.text("Meu perfil", font_size="0.9rem", color="rgba(248,249,250,0.7)",
                                _hover={"color": "#F8F9FA"}),
                        href="/perfil",
                    ),
                    rx.link(
                        rx.text("Meu armário", font_size="0.9rem", color="rgba(248,249,250,0.7)",
                                _hover={"color": "#F8F9FA"}),
                        href="/armario",
                    ),
                    rx.button(
                        "Sair",
                        on_click=AuthState.logout,
                        variant="ghost",
                        color="rgba(248,249,250,0.7)",
                        font_size="0.9rem",
                        _hover={"color": "#F8F9FA"},
                    ),
                    spacing="4",
                    align_items="center",
                ),
                width="100%",
                align_items="center",
            ),
            background=INK,
            padding_x=["1.2rem", "2rem", "3rem"],
            padding_y="1rem",
            position="sticky",
            top="0",
            z_index="100",
            box_shadow="0 2px 16px rgba(15,26,51,0.18)",
        ),

        # ── Conteúdo ──────────────────────────────────────────────────────
        rx.center(
            rx.vstack(
                # Cabeçalho da página
                rx.hstack(
                    rx.vstack(
                        rx.heading(
                            "Meus Endereços",
                            font_family=DISPLAY,
                            font_size="1.8rem",
                            color=INK,
                        ),
                        rx.text(
                            "Gerencie seus endereços de entrega.",
                            color=MUTED,
                            font_size="0.95rem",
                        ),
                        spacing="1",
                        align_items="flex-start",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.cond(
                            AddressState.show_form,
                            rx.hstack(rx.icon("x", size=16), rx.text("Cancelar"), spacing="2"),
                            rx.hstack(rx.icon("plus", size=16), rx.text("Novo Endereço"), spacing="2"),
                        ),
                        on_click=AddressState.toggle_form,
                        background=rx.cond(AddressState.show_form, "#e5e7eb", THREAD),
                        color=rx.cond(AddressState.show_form, INK, INK),
                        border_radius="12px",
                        font_weight="700",
                        height="42px",
                        padding_x="1.2rem",
                        id="btn-novo-endereco",
                    ),
                    width="100%",
                    align_items="flex-start",
                ),

                # Mensagem de sucesso global
                rx.cond(
                    AddressState.address_success != "",
                    rx.callout.root(
                        rx.callout.icon(rx.icon("circle-check")),
                        rx.callout.text(AddressState.address_success),
                        color="green", variant="soft",
                    ),
                ),

                # Formulário (condicional)
                rx.cond(AddressState.show_form, _address_form()),

                # ── Loading / Erro / Lista de endereços ───────────────────
                rx.cond(
                    AddressState.address_loading,
                    rx.center(
                        rx.vstack(
                            rx.spinner(size="3"),
                            rx.text("Carregando endereços…", color=MUTED, font_size="0.9rem"),
                            spacing="3",
                            align_items="center",
                        ),
                        padding_y="3rem",
                    ),
                    rx.cond(
                        AddressState.address_error != "",
                        rx.callout.root(
                            rx.callout.icon(rx.icon("triangle-alert")),
                            rx.callout.text(AddressState.address_error),
                            color="red", variant="soft",
                        ),
                        rx.cond(
                            AddressState.addresses.length() == 0,
                            rx.center(
                                rx.vstack(
                                    rx.text("📍", font_size="2.5rem"),
                                    rx.text(
                                        "Nenhum endereço cadastrado ainda.",
                                        color=MUTED,
                                        font_size="1rem",
                                        font_weight="600",
                                    ),
                                    rx.text(
                                        "Clique em 'Novo Endereço' para começar.",
                                        color=MUTED,
                                        font_size="0.88rem",
                                    ),
                                    spacing="2",
                                    align_items="center",
                                ),
                                padding_y="3rem",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.foreach(AddressState.addresses, _address_card),
                                spacing="3",
                                width="100%",
                            ),
                        ),
                    ),
                ),

                spacing="5",
                width="100%",
                max_width="760px",
                padding_y=["1.5rem", "2rem"],
                padding_x=["1rem", "1.5rem", "2rem"],
            ),
        ),
        min_height="100vh",
        background=CHALK,
        font_family=BODY,
    )


# ── Inicialização do Aplicativo Reflex ───────────────────────────────────
def workspace_navbar() -> rx.Component:
    links = [
        ("Loja", "/loja", "shopping-bag"),
        ("Meu armário", "/armario", "shirt"),
        ("Meu perfil", "/perfil", "user-round"),
        ("Endereços", "/enderecos", "map-pin"),
    ]
    link_components = [
        rx.link(
            rx.hstack(
                rx.icon(icon, size=16),
                rx.text(label, font_size="0.86rem", font_weight="600"),
                spacing="2",
            ),
            href=href,
            color="rgba(248,249,250,0.82)",
            _hover={"color": THREAD},
        )
        for label, href, icon in links
    ]
    return rx.box(
        rx.hstack(
            rx.link(
                rx.hstack(
                    rx.html(LOGO_SVG),
                    rx.vstack(
                        rx.text("OSDROUPA", font_family=DISPLAY, font_weight="800", color=CHALK, letter_spacing="0.06em"),
                        rx.text("SEU UNIVERSO, SEU ESTILO", font_size="0.62rem", font_weight="700", color=THREAD, letter_spacing="0.12em"),
                        spacing="0",
                        align_items="flex-start",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                href="/",
            ),
            rx.spacer(),
            rx.hstack(
                *link_components,
                rx.button(
                    rx.hstack(
                        rx.icon("log-out", size=16),
                        rx.text("Sair", font_size="0.86rem", font_weight="600"),
                        spacing="2",
                    ),
                    on_click=AuthState.logout,
                    background="rgba(255,255,255,0.07)",
                    color=CHALK,
                    border="1px solid rgba(255,255,255,0.12)",
                    border_radius="12px",
                    cursor="pointer",
                ),
                spacing="5",
                align_items="center",
                wrap="wrap",
                justify="end",
            ),
            width="100%",
            max_width="1240px",
            margin_x="auto",
            align_items="center",
        ),
        padding_y="1rem",
        padding_x=["1rem", "1.5rem", "2rem"],
        background="rgba(15,26,51,0.96)",
        border_bottom="1px solid rgba(255,255,255,0.08)",
        position="sticky",
        top="0",
        z_index="100",
        width="100%",
    )


def auth_loading_screen() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.spinner(size="3", color=THREAD),
            rx.text("Validando sua conta…", color=MUTED, font_weight="600"),
            spacing="3",
            align="center",
        ),
        min_height="55vh",
        width="100%",
    )


def profile_data_card(label: str, value, icon_name: str) -> rx.Component:
    return rx.hstack(
        rx.center(
            rx.icon(icon_name, size=18, color=THREAD),
            width="42px",
            height="42px",
            border_radius="13px",
            background="rgba(233,162,59,0.12)",
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(label.upper(), font_size="0.68rem", font_weight="800", letter_spacing="0.1em", color=MUTED),
            rx.text(value, font_size="0.96rem", font_weight="600", color=INK),
            spacing="1",
            align_items="flex-start",
        ),
        spacing="3",
        align="center",
        width="100%",
        padding="1rem 0",
        border_bottom="1px solid rgba(15,26,51,0.07)",
    )


def profile_page() -> rx.Component:
    identity_card = rx.box(
        rx.vstack(
            rx.center(
                rx.text(AuthState.user_display_name[0], font_family=DISPLAY, font_size="2.5rem", font_weight="800", color=INK),
                width="92px",
                height="92px",
                border_radius="28px",
                background=f"linear-gradient(145deg, {THREAD}, #F5CB81)",
                box_shadow="0 12px 30px rgba(233,162,59,0.28)",
            ),
            rx.heading(AuthState.user_display_name, font_family=DISPLAY, font_size="1.6rem", color=INK, text_align="center"),
            rx.text(AuthState.user_email, color=MUTED, font_size="0.9rem", text_align="center"),
            rx.divider(margin_y="0.4rem"),
            rx.hstack(
                rx.icon("shield-check", size=17, color=OK),
                rx.text("Sessão ativa e confirmada pelo Xano", font_size="0.82rem", color=OK, font_weight="600"),
                spacing="2",
                align="center",
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        background="#FFFFFF",
        border="1px solid rgba(15,26,51,0.07)",
        border_radius="24px",
        padding=["1.4rem", "2rem"],
        box_shadow="0 16px 42px rgba(15,26,51,0.06)",
    )
    account_card = rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text("IDENTIDADE", color=THREAD, font_size="0.68rem", font_weight="800", letter_spacing="0.14em"),
                    rx.heading("Dados da conta", font_family=DISPLAY, font_size="1.35rem", color=INK),
                    spacing="1",
                    align_items="flex-start",
                ),
                rx.spacer(),
                rx.icon("contact-round", size=22, color=DENIM),
                width="100%",
                align="center",
            ),
            profile_data_card("Nome completo", AuthState.user_display_name, "user-round"),
            profile_data_card("E-mail", AuthState.user_email, "mail"),
            profile_data_card("Celular", AuthState.profile_phone, "phone"),
            profile_data_card("Conta vinculada", AuthState.account_id_label, "building-2"),
            spacing="1",
            align_items="stretch",
            width="100%",
        ),
        background="#FFFFFF",
        border="1px solid rgba(15,26,51,0.07)",
        border_radius="24px",
        padding=["1.4rem", "2rem"],
        box_shadow="0 16px 42px rgba(15,26,51,0.06)",
    )
    wardrobe_callout = rx.box(
        rx.hstack(
            rx.vstack(
                rx.text("PRÓXIMO PASSO", color=THREAD, font_size="0.68rem", font_weight="800", letter_spacing="0.14em"),
                rx.heading("Seu armário está esperando por você.", font_family=DISPLAY, font_size=["1.2rem", "1.55rem"], color=CHALK),
                rx.text("Organize suas peças e comece a construir seu acervo digital.", color="rgba(248,249,250,0.72)", font_size="0.9rem"),
                spacing="2",
                align_items="flex-start",
            ),
            rx.spacer(),
            rx.link(
                rx.button(
                    rx.hstack(rx.text("Abrir meu armário"), rx.icon("arrow-right", size=16), spacing="2"),
                    background=THREAD,
                    color=INK,
                    font_weight="700",
                    border_radius="100px",
                    height="46px",
                    padding_x="1.3rem",
                ),
                href="/armario",
            ),
            width="100%",
            align="center",
            wrap="wrap",
        ),
        background=f"linear-gradient(120deg, {INK}, {DENIM})",
        border="1px solid rgba(233,162,59,0.26)",
        border_radius="22px",
        padding=["1.3rem", "1.8rem"],
    )
    content = rx.box(
        workspace_navbar(),
        rx.center(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("SEU ESPAÇO OSDROUPA", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.16em"),
                        rx.heading("Seu estilo, sua conta.", font_family=DISPLAY, font_size=["2.2rem", "3.5rem"], color=INK, letter_spacing="-0.04em"),
                        rx.text("As informações da sua conta, reunidas com clareza em um só lugar.", color=MUTED, font_size="1rem", line_height="1.6"),
                        spacing="2",
                        align_items="flex-start",
                    ),
                    rx.badge(
                        rx.hstack(rx.icon("badge-check", size=15), rx.text("Conta verificada"), spacing="1"),
                        color_scheme="green",
                        variant="soft",
                        size="2",
                    ),
                    width="100%",
                    align_items="center",
                    wrap="wrap",
                ),
                rx.grid(
                    identity_card,
                    account_card,
                    columns={"initial": "1", "md": "0.8fr 1.2fr"},
                    spacing="5",
                    width="100%",
                ),
                wardrobe_callout,
                spacing="5",
                width="100%",
                max_width="1160px",
                padding_y=["2rem", "3.5rem"],
                padding_x=["1rem", "1.5rem", "2rem"],
            ),
        ),
        min_height="100vh",
        background="#F7F5EF",
    )
    return rx.box(
        rx.el.style(CSS),
        rx.cond(AuthState.account_validated, content, auth_loading_screen()),
        min_height="100vh",
        background="#F7F5EF",
        font_family=BODY,
    )


def wardrobe_item_card(item: dict) -> rx.Component:
    garment_art = rx.hstack(
        rx.center(
            rx.icon("shirt", size=46, color=DENIM),
            width="100%",
            height="150px",
            border_radius="17px",
            background="linear-gradient(145deg, #F1EDE2, #E5EAF1)",
        ),
        rx.button(
            rx.icon("trash-2", size=16),
            on_click=WardrobeState.remove_item(item["id"]),
            variant="ghost",
            color=MUTED,
            position="absolute",
            top="10px",
            right="10px",
            border_radius="10px",
            _hover={"background": "rgba(180,55,47,0.1)", "color": ERROR},
            aria_label="Remover peça",
        ),
        position="relative",
        width="100%",
    )
    return rx.box(
        rx.vstack(
            garment_art,
            rx.hstack(
                rx.badge(item["category"], color_scheme="amber", variant="soft", size="1"),
                rx.spacer(),
                rx.text(item["status"], font_size="0.72rem", color=OK, font_weight="600"),
                width="100%",
                align="center",
            ),
            rx.heading(item["name"], font_family=DISPLAY, font_size="1.12rem", color=INK),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
        position="relative",
        background="#FFFFFF",
        border="1px solid rgba(15,26,51,0.08)",
        border_radius="22px",
        padding="1rem",
        box_shadow="0 10px 26px rgba(15,26,51,0.05)",
        transition="transform 0.2s ease, box-shadow 0.2s ease",
        _hover={"transform": "translateY(-3px)", "box_shadow": "0 16px 36px rgba(15,26,51,0.1)"},
    )


def wardrobe_form() -> rx.Component:
    category_buttons = [
        rx.button(
            category,
            on_click=WardrobeState.set_new_item_category(category),
            background=rx.cond(WardrobeState.new_item_category == category, INK, "#F0F1F3"),
            color=rx.cond(WardrobeState.new_item_category == category, CHALK, MUTED),
            border_radius="100px",
            size="2",
        )
        for category in WARDROBE_CATEGORIES
    ]
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("Uma nova peça", font_family=DISPLAY, font_size="1.25rem", color=INK),
                rx.spacer(),
                rx.button(rx.icon("x", size=17), on_click=WardrobeState.toggle_item_form, variant="ghost", color=MUTED),
                width="100%",
                align="center",
            ),
            field("Nome da peça", placeholder="Ex.: Camisa de linho cru", value=WardrobeState.new_item_name, on_change=WardrobeState.set_new_item_name),
            rx.text("Escolha uma categoria", font_size="0.82rem", font_weight="700", color=INK),
            rx.flex(*category_buttons, wrap="wrap", spacing="2", width="100%"),
            rx.cond(
                WardrobeState.wardrobe_error != "",
                rx.text(WardrobeState.wardrobe_error, color=ERROR, font_size="0.84rem", role="alert"),
            ),
            rx.hstack(
                rx.button("Cancelar", on_click=WardrobeState.toggle_item_form, variant="ghost", color=MUTED),
                rx.button("Salvar peça", on_click=WardrobeState.add_item, background=THREAD, color=INK, font_weight="700", border_radius="11px"),
                justify="end",
                width="100%",
            ),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
        background="#FFFFFF",
        border="1px solid rgba(15,26,51,0.08)",
        border_radius="22px",
        padding=["1.2rem", "1.6rem"],
        width="100%",
        box_shadow="0 12px 28px rgba(15,26,51,0.06)",
    )


def wardrobe_empty_state() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.center(
                rx.icon("shirt", size=32, color=DENIM),
                width="72px",
                height="72px",
                border_radius="22px",
                background="rgba(233,162,59,0.15)",
            ),
            rx.heading("Seu armário começa com uma peça.", font_family=DISPLAY, font_size="1.35rem", color=INK, text_align="center"),
            rx.text("Adicione uma roupa e organize seu acervo por categoria.", color=MUTED, font_size="0.9rem", text_align="center"),
            rx.button("Adicionar minha primeira peça", on_click=WardrobeState.toggle_item_form, background=INK, color=CHALK, border_radius="100px", margin_top="0.4rem"),
            spacing="3",
            align="center",
        ),
        background="#FFFFFF",
        border="1px dashed rgba(31,53,96,0.24)",
        border_radius="24px",
        padding=["2rem", "3.5rem"],
        width="100%",
    )


def wardrobe_page() -> rx.Component:
    filters = ["Todas", *WARDROBE_CATEGORIES]
    filter_buttons = [
        rx.button(
            category,
            on_click=WardrobeState.set_wardrobe_filter(category),
            background=rx.cond(WardrobeState.wardrobe_filter == category, INK, "#FFFFFF"),
            color=rx.cond(WardrobeState.wardrobe_filter == category, CHALK, MUTED),
            border="1px solid rgba(15,26,51,0.08)",
            border_radius="100px",
            size="2",
        )
        for category in filters
    ]
    search_input = rx.hstack(
        rx.icon("search", size=17, color=MUTED),
        rx.input(
            value=WardrobeState.wardrobe_search,
            on_change=WardrobeState.set_wardrobe_search,
            placeholder="Buscar uma peça",
            variant="soft",
            border="none",
            background="transparent",
            width="100%",
        ),
        background="#FFFFFF",
        border="1px solid rgba(15,26,51,0.09)",
        border_radius="13px",
        padding_x="0.8rem",
        width=["100%", "300px"],
        align="center",
    )
    collection_banner = rx.box(
        rx.hstack(
            rx.vstack(
                rx.text("COLEÇÃO", color=THREAD, font_size="0.66rem", font_weight="800", letter_spacing="0.14em"),
                rx.heading("Seu guarda-roupa digital", font_family=DISPLAY, font_size="1.4rem", color=CHALK),
                rx.text("Cada peça no lugar certo, pronta para inspirar o próximo look.", color="rgba(248,249,250,0.7)", font_size="0.86rem"),
                spacing="1",
                align_items="flex-start",
            ),
            rx.spacer(),
            rx.button(
                rx.hstack(rx.icon("plus", size=17), rx.text("Adicionar peça"), spacing="2"),
                on_click=WardrobeState.toggle_item_form,
                background=THREAD,
                color=INK,
                font_weight="700",
                border_radius="100px",
                height="46px",
                padding_x="1.3rem",
            ),
            width="100%",
            align="center",
            wrap="wrap",
        ),
        background=f"linear-gradient(120deg, {INK}, {DENIM})",
        border_radius="23px",
        padding=["1.3rem", "1.8rem"],
        width="100%",
        box_shadow="0 20px 45px rgba(15,26,51,0.16)",
    )
    empty_state = rx.cond(
        WardrobeState.wardrobe_count == 0,
        wardrobe_empty_state(),
        rx.center(
            rx.vstack(
                rx.icon("search-x", size=30, color=DENIM),
                rx.heading("Nenhuma peça encontrada.", font_family=DISPLAY, font_size="1.25rem", color=INK),
                rx.text("Experimente outro termo ou limpe os filtros.", color=MUTED, font_size="0.88rem"),
                rx.button(
                    "Limpar busca e filtros",
                    on_click=WardrobeState.reset_wardrobe_filters,
                    background=INK,
                    color=CHALK,
                    border_radius="100px",
                ),
                spacing="3",
                align="center",
            ),
            background="#FFFFFF",
            border="1px dashed rgba(31,53,96,0.24)",
            border_radius="24px",
            padding=["2rem", "3.5rem"],
            width="100%",
        ),
    )
    content = rx.box(
        workspace_navbar(),
        rx.center(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("ACERVO PESSOAL", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.16em"),
                        rx.heading("Vista o que é seu.", font_family=DISPLAY, font_size=["2.4rem", "3.8rem"], color=INK, letter_spacing="-0.045em"),
                        rx.text("Um lugar leve para organizar as peças que contam a sua história.", color=MUTED, font_size="1rem", line_height="1.6"),
                        spacing="2",
                        align_items="flex-start",
                    ),
                    rx.vstack(
                        rx.text(WardrobeState.wardrobe_count, font_family=DISPLAY, font_size="2.4rem", font_weight="800", color=INK),
                        rx.text("PEÇAS NO ARMÁRIO", font_size="0.65rem", font_weight="800", color=MUTED, letter_spacing="0.1em"),
                        spacing="0",
                        align="center",
                        background="#FFFFFF",
                        border="1px solid rgba(15,26,51,0.08)",
                        border_radius="18px",
                        padding="0.9rem 1.3rem",
                    ),
                    width="100%",
                    align="center",
                    wrap="wrap",
                ),
                collection_banner,
                rx.link(
                    rx.hstack(
                        rx.icon("radio-tower", size=18, color=DENIM),
                        rx.text("Dispositivos do armário inteligente", color=INK, font_weight="700"),
                        rx.spacer(),
                        rx.text("Ver conexões →", color=DENIM, font_weight="700", font_size="0.86rem"),
                        width="100%",
                        align="center",
                    ),
                    href="/dispositivos",
                    background="#FFFFFF",
                    border="1px solid rgba(15,26,51,0.08)",
                    border_radius="16px",
                    padding="1rem 1.2rem",
                    width="100%",
                    _hover={"border_color": "rgba(31,53,96,0.35)"},
                ),
                rx.cond(
                    WardrobeState.wardrobe_remote_ready,
                    rx.callout(WardrobeState.wardrobe_sync_notice, icon="cloud-check", color="green", width="100%"),
                    rx.callout(WardrobeState.wardrobe_sync_notice, icon="cloud-off", color="amber", width="100%"),
                ),
                rx.cond(
                    WardrobeState.wardrobe_error != "",
                    rx.callout(WardrobeState.wardrobe_error, icon="triangle_alert", color="red", width="100%"),
                ),
                rx.cond(WardrobeState.show_item_form, wardrobe_form(), rx.fragment()),
                rx.hstack(
                    search_input,
                    rx.flex(*filter_buttons, wrap="wrap", spacing="2", width="100%"),
                    direction={"initial": "column", "md": "row"},
                    width="100%",
                    align="center",
                    justify="between",
                    spacing="3",
                ),
                rx.cond(
                    WardrobeState.filtered_items.length() == 0,
                    empty_state,
                    rx.grid(
                        rx.foreach(WardrobeState.filtered_items, wardrobe_item_card),
                        columns={"initial": "1", "sm": "2", "lg": "3"},
                        spacing="4",
                        width="100%",
                    ),
                ),
                rx.text("Seu acervo fica salvo neste navegador e associado a esta conta.", color=MUTED, font_size="0.78rem", text_align="center", width="100%"),
                spacing="5",
                align_items="stretch",
                width="100%",
                max_width="1160px",
                padding_y=["2rem", "3.5rem"],
                padding_x=["1rem", "1.5rem", "2rem"],
            ),
        ),
        min_height="100vh",
        background="#F7F5EF",
    )
    return rx.box(
        rx.el.style(CSS),
        rx.cond(AuthState.account_validated, content, auth_loading_screen()),
        min_height="100vh",
        background="#F7F5EF",
        font_family=BODY,
    )


def store_navbar() -> rx.Component:
    return rx.hstack(
        rx.link(
            rx.hstack(
                rx.html(LOGO_SVG),
                rx.vstack(
                    rx.text("OSDROUPA", font_family=DISPLAY, font_weight="700", font_size="1.15rem", color=CHALK),
                    rx.text("Loja e alfaiataria", font_size="0.7rem", color="rgba(248,249,250,0.65)"),
                    spacing="0", align_items="flex-start",
                ),
                spacing="2", align_items="center",
            ),
            href="/", _hover={"opacity": "0.85"},
        ),
        rx.spacer(),
        rx.link("Loja", href="/loja", color=CHALK, font_weight="600"),
        rx.link("Inspiração", href="/inspiracao", color=CHALK, font_weight="600"),
        rx.link(
            rx.hstack(
                rx.icon("shopping-bag", size=17, color=THREAD),
                rx.text("Sacola", color=CHALK, font_weight="600"),
                rx.badge(StoreState.cart_count, color_scheme="amber", variant="solid"),
                spacing="2", align_items="center",
            ),
            href="/carrinho", _hover={"opacity": "0.85"},
        ),
        rx.cond(
            AuthState.account_validated,
            rx.hstack(
                rx.link("Meu perfil", href="/perfil", color=CHALK, font_weight="600"),
                rx.link("Meu armário", href="/armario", color=CHALK, font_weight="600"),
                rx.link("Pedidos", href="/pedidos", color=CHALK, font_weight="600"),
                rx.button("Sair", on_click=AuthState.logout, variant="ghost", color="#FFB4A9"),
                spacing="3", align_items="center",
            ),
            rx.link("Entrar", href="/login", color=THREAD, font_weight="700"),
        ),
        width="100%", padding_y="1rem", padding_x=["1rem", "1.5rem", "2.5rem"],
        background=INK, border_bottom="1px solid rgba(255,255,255,0.1)",
        position="sticky", top="0", z_index="100", align_items="center", spacing="5",
    )


def store_product_card(product: dict) -> rx.Component:
    image_panel = rx.cond(
        product["image_url"] != "",
        rx.image(
            src=product["image_url"], alt=product["name"], width="100%", height="250px",
            object_fit="cover", border_radius="18px",
        ),
        rx.center(
            rx.icon("shirt", size=54, color=DENIM),
            width="100%", height="250px", border_radius="18px",
            background="linear-gradient(145deg, #E8EAF0, #F3F0E8)",
        ),
    )
    return rx.box(
        rx.vstack(
            image_panel,
            rx.hstack(
                rx.badge(
                    product["availability"],
                    color_scheme=rx.cond(product["availability"] == "Sem estoque", "gray", rx.cond(product["availability"] == "Sob encomenda", "amber", "green")),
                    variant="soft",
                ),
                rx.badge(product["category"], color_scheme="gray", variant="soft"),
                rx.spacer(),
                rx.text(product["price_display"], color=INK, font_weight="700", font_size="1.05rem"),
                width="100%", align_items="center",
            ),
            rx.heading(product["name"], font_family=DISPLAY, font_size="1.2rem", color=INK, width="100%"),
            rx.text(
                product["description"], color=MUTED, font_size="0.9rem", line_height="1.5",
                min_height="2.7rem", width="100%", overflow="hidden",
            ),
            rx.hstack(
                rx.text(
                    rx.cond(
                        product["availability"] == "Disponível agora",
                        rx.cond(product["stock"] == "1", "1 unidade disponível", product["stock"] + " unidades disponíveis"),
                        rx.cond(product["availability"] == "Sob encomenda", "Produzido sob encomenda", "Temporariamente indisponível"),
                    ),
                    font_size="0.78rem", color=MUTED,
                ),
                rx.spacer(),
                rx.button(
                    "Ver produto", on_click=StoreState.open_product(product["id"]),
                    background=INK, color=CHALK, border_radius="100px", font_weight="700",
                    _hover={"background": DENIM},
                ),
                width="100%", align_items="center",
            ),
            spacing="3", align_items="stretch", width="100%",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="24px",
        padding="1rem", box_shadow="0 12px 32px rgba(15,26,51,0.06)",
        transition="transform 0.2s ease, box-shadow 0.2s ease",
        _hover={"transform": "translateY(-3px)", "box_shadow": "0 18px 42px rgba(15,26,51,0.11)"},
        width="100%",
    )


def store_page() -> rx.Component:
    category_options = ["Todas", *STORE_CATEGORIES]
    availability_options = ["Todos", "Disponível agora", "Sob encomenda", "Sem estoque"]
    sort_options = ["Recomendados", "Menor preço", "Maior preço"]
    return rx.box(
        rx.el.style(CSS),
        store_navbar(),
        rx.center(
            rx.vstack(
                rx.box(
                    rx.vstack(
                        rx.badge("COLEÇÃO OSDROUPA", color_scheme="amber", variant="soft", size="2"),
                        rx.heading(
                            "Uma escolha que combina com você.",
                            font_family=DISPLAY, font_size=["2.1rem", "2.7rem", "3.3rem"],
                            color=CHALK, line_height="1.05", max_width="720px",
                        ),
                        rx.text(
                            "Explore os produtos disponíveis e encontre sua próxima peça favorita.",
                            color="rgba(248,249,250,0.75)", font_size=["0.95rem", "1.05rem"], max_width="580px", line_height="1.6",
                        ),
                        spacing="4", align_items="flex-start",
                    ),
                    width="100%", padding=["1.7rem", "2.5rem", "3.5rem"], border_radius="28px",
                    background=f"linear-gradient(125deg, {INK} 0%, {DENIM} 68%, #526A94 100%)",
                    border="1px solid rgba(233,162,59,0.25)",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.heading("Escolha com calma.", font_family=DISPLAY, color=INK, font_size="1.7rem"),
                            rx.text("Produtos do catálogo OSDROUPA", color=MUTED, font_size="0.9rem"),
                            spacing="1", align_items="flex-start",
                        ),
                        rx.spacer(),
                        rx.input(
                            placeholder="Buscar produto", value=StoreState.store_search,
                            on_change=StoreState.set_store_search, width=["100%", "280px"],
                            background="#FFFFFF", border="1px solid rgba(15,26,51,0.12)", border_radius="100px",
                            padding_x="1rem", height="44px", aria_label="Buscar no catálogo",
                        ),
                        width="100%", align_items="center", flex_wrap="wrap", spacing="4",
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Categoria", font_size="0.75rem", color=MUTED, font_weight="700"),
                            rx.select(
                                category_options, value=StoreState.category_filter,
                                on_change=StoreState.set_category_filter, width="190px",
                            ),
                            spacing="1", align_items="flex-start",
                        ),
                        rx.vstack(
                            rx.text("Disponibilidade", font_size="0.75rem", color=MUTED, font_weight="700"),
                            rx.select(
                                availability_options, value=StoreState.availability_filter,
                                on_change=StoreState.set_availability_filter, width="220px",
                            ),
                            spacing="1", align_items="flex-start",
                        ),
                        rx.vstack(
                            rx.text("Ordenar por", font_size="0.75rem", color=MUTED, font_weight="700"),
                            rx.select(
                                sort_options, value=StoreState.price_sort,
                                on_change=StoreState.set_price_sort, width="210px",
                            ),
                            spacing="1", align_items="flex-start",
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.hstack(rx.icon("refresh-cw", size=15), rx.text("Atualizar"), spacing="2"),
                            on_click=StoreState.load_catalog, variant="ghost", color=DENIM,
                        ),
                        width="100%", align_items="end", flex_wrap="wrap", spacing="4",
                    ),
                    rx.cond(
                        StoreState.products.length() > 0,
                        rx.cond(
                            StoreState.catalog_unclassified_count > 0,
                            rx.box(
                                rx.text(
                                    "Alguns itens foram ocultados porque não têm uma categoria de vestuário válida no Xano.",
                                    color="#76521A", font_size="0.86rem",
                                ),
                                background="#FFF6E4", border="1px solid #F1D8A5", border_radius="14px",
                                padding="0.85rem 1rem", width="100%",
                            ),
                            rx.box(display="none"),
                        ),
                        rx.box(display="none"),
                    ),
                    rx.cond(
                        StoreState.catalog_loading,
                        rx.center(rx.vstack(rx.spinner(size="3", color=THREAD), rx.text("Carregando catálogo…", color=MUTED), spacing="3"), width="100%", min_height="280px"),
                        rx.cond(
                            StoreState.catalog_error != "",
                            rx.center(rx.vstack(
                                rx.icon("cloud-off", size=34, color=ERROR),
                                rx.text(StoreState.catalog_error, color=INK, text_align="center"),
                                rx.button("Tentar novamente", on_click=StoreState.load_catalog, background=INK, color=CHALK, border_radius="100px"),
                                spacing="3", align_items="center",
                            ), width="100%", min_height="280px"),
                            rx.cond(
                                StoreState.products.length() == 0,
                                rx.cond(
                                    StoreState.catalog_setup_required,
                                    rx.center(rx.vstack(
                                        rx.icon("shirt", size=38, color=DENIM),
                                        rx.heading("A loja de roupas está sendo preparada.", font_family=DISPLAY, color=INK, text_align="center"),
                                        rx.text("O catálogo do Xano ainda não tem categorias válidas de roupas, calçados ou acessórios. Atualize os produtos para exibi-los aqui.", color=MUTED, text_align="center", max_width="620px"),
                                        spacing="3", align_items="center",
                                    ), width="100%", min_height="280px"),
                                    rx.center(rx.vstack(
                                        rx.icon("package-open", size=34, color=DENIM),
                                        rx.heading("A coleção está sendo preparada.", font_family=DISPLAY, color=INK),
                                        rx.text("Volte em breve para conhecer as novidades.", color=MUTED),
                                        spacing="3", align_items="center",
                                    ), width="100%", min_height="280px"),
                                ),
                                rx.cond(
                                    StoreState.filtered_products.length() == 0,
                                    rx.center(rx.vstack(
                                        rx.icon("search-x", size=32, color=MUTED),
                                        rx.text("Nenhum produto corresponde a essa busca.", color=INK),
                                        rx.button("Limpar busca", on_click=StoreState.set_store_search(""), variant="ghost", color=DENIM),
                                        spacing="2", align_items="center",
                                    ), width="100%", min_height="240px"),
                                    rx.grid(
                                        rx.foreach(StoreState.filtered_products, store_product_card),
                                        columns={"initial": "1", "sm": "2", "lg": "3"},
                                        spacing="4", width="100%",
                                    ),
                                ),
                            ),
                        ),
                    ),
                    spacing="5", width="100%", align_items="stretch",
                ),
                rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.heading("Um armário com mais intenção.", font_family=DISPLAY, color=CHALK, font_size="1.5rem"),
                            rx.text("Guarde suas peças favoritas e monte sua coleção pessoal.", color="rgba(248,249,250,0.72)"),
                            spacing="2", align_items="flex-start",
                        ),
                        rx.spacer(),
                        rx.link("Conhecer meu armário", href="/armario", color=INK, font_weight="700", background=THREAD, padding="0.8rem 1.2rem", border_radius="100px"),
                        width="100%", align_items="center", flex_wrap="wrap", spacing="4",
                    ),
                    background=DENIM, border_radius="22px", padding=["1.2rem", "1.8rem"], width="100%",
                ),
                spacing="7", width="100%", max_width="1220px", padding_y=["1.5rem", "2.5rem", "3.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
            ), width="100%",
        ),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def product_detail_page() -> rx.Component:
    product_image = rx.cond(
        StoreState.selected_product["image_url"] != "",
        rx.image(
            src=StoreState.selected_product["image_url"], alt=StoreState.selected_product["name"],
            width="100%", height=["300px", "420px"], object_fit="cover", border_radius="24px",
        ),
        rx.center(rx.icon("shirt", size=72, color=DENIM), width="100%", height=["300px", "420px"], border_radius="24px", background="linear-gradient(145deg, #E8EAF0, #F3F0E8)"),
    )
    detail = rx.grid(
        product_image,
        rx.vstack(
            rx.badge(
                StoreState.selected_product["availability"],
                color_scheme=rx.cond(StoreState.selected_product["availability"] == "Sem estoque", "gray", rx.cond(StoreState.selected_product["availability"] == "Sob encomenda", "amber", "green")),
                variant="soft", size="2",
            ),
            rx.badge(StoreState.selected_product["category"], color_scheme="gray", variant="soft"),
            rx.heading(StoreState.selected_product["name"], font_family=DISPLAY, font_size=["2rem", "2.6rem"], color=INK, line_height="1.08"),
            rx.text(StoreState.selected_product["description"], color=MUTED, line_height="1.7", white_space="pre-wrap"),
            rx.text(StoreState.selected_product["price_display"], color=INK, font_family=DISPLAY, font_size="1.8rem", font_weight="700"),
            rx.text(
                rx.cond(
                    StoreState.selected_product["availability"] == "Disponível agora",
                    rx.cond(StoreState.selected_product["stock"] == "1", "1 unidade disponível", StoreState.selected_product["stock"] + " unidades disponíveis"),
                    rx.cond(StoreState.selected_product["availability"] == "Sob encomenda", "Produzido sob encomenda", "Temporariamente indisponível"),
                ),
                color=MUTED, font_size="0.88rem",
            ),
            rx.button(
                rx.hstack(rx.icon("shopping-bag", size=17), rx.text("Adicionar à sacola"), spacing="2"),
                on_click=StoreState.add_to_cart(StoreState.selected_product["id"]),
                disabled=StoreState.selected_product["availability"] == "Sem estoque",
                background=THREAD, color=INK, border_radius="100px", padding="0.9rem 1.4rem", font_weight="700",
                _hover={"background": "#F1B958"},
            ),
            rx.cond(StoreState.cart_feedback != "", rx.text(StoreState.cart_feedback, color=OK, font_size="0.85rem", role="status")),
            rx.text("Preço e disponibilidade serão confirmados novamente antes da compra.", color=MUTED, font_size="0.78rem", line_height="1.5"),
            spacing="4", align_items="flex-start", justify="center", width="100%",
        ),
        columns={"initial": "1", "md": "2"}, spacing="6", width="100%", align_items="center",
    )
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.button("← Voltar à loja", on_click=rx.redirect("/loja"), variant="ghost", color=DENIM, align_self="flex-start"),
            rx.cond(
                StoreState.product_loading,
                rx.center(rx.spinner(size="3", color=THREAD), width="100%", min_height="340px"),
                rx.cond(
                    StoreState.product_error != "",
                    rx.center(rx.vstack(rx.icon("package-x", size=36, color=ERROR), rx.text(StoreState.product_error, color=INK), rx.link("Ver catálogo", href="/loja", color=DENIM), spacing="3", align_items="center"), width="100%", min_height="340px"),
                    detail,
                ),
            ),
            spacing="5", width="100%", max_width="1120px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def cart_line_card(item: dict) -> rx.Component:
    product_image = rx.cond(
        item["image_url"] != "",
        rx.image(src=item["image_url"], alt=item["name"], width="112px", height="124px", object_fit="cover", border_radius="16px"),
        rx.center(rx.icon("shirt", size=34, color=DENIM), width="112px", height="124px", border_radius="16px", background="#E9ECF2"),
    )
    return rx.box(
        rx.hstack(
            product_image,
            rx.vstack(
                rx.heading(item["name"], font_family=DISPLAY, color=INK, font_size="1.08rem"),
                rx.text(item["availability"], color=MUTED, font_size="0.78rem"),
                rx.text(item["price_display"], color=INK, font_weight="700"),
                rx.hstack(
                    rx.button("−", on_click=StoreState.decrement_cart_item(item["product_id"]), size="1", variant="outline", aria_label="Diminuir quantidade"),
                    rx.text(item["quantity"], min_width="28px", text_align="center", font_weight="700"),
                    rx.button("+", on_click=StoreState.increment_cart_item(item["product_id"]), size="1", variant="outline", aria_label="Aumentar quantidade"),
                    rx.spacer(),
                    rx.button("Remover", on_click=StoreState.remove_cart_item(item["product_id"]), variant="ghost", color=ERROR, size="1"),
                    width="100%", align_items="center", spacing="2",
                ),
                spacing="2", align_items="flex-start", width="100%",
            ),
            width="100%", align_items="center", spacing="4",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1rem", width="100%",
    )


def cart_page() -> rx.Component:
    cart_content = rx.grid(
        rx.vstack(
            rx.foreach(StoreState.cart_items, cart_line_card),
            rx.cond(StoreState.cart_feedback != "", rx.text(StoreState.cart_feedback, color=OK, role="status")),
            spacing="3", width="100%", align_items="stretch",
        ),
        rx.box(
            rx.vstack(
                rx.heading("Resumo da sacola", font_family=DISPLAY, color=INK, font_size="1.25rem"),
                rx.hstack(rx.text("Produtos", color=MUTED), rx.spacer(), rx.text(StoreState.cart_total_display, color=INK, font_weight="700"), width="100%"),
                rx.divider(),
                rx.hstack(rx.text("Total parcial", color=INK, font_weight="700"), rx.spacer(), rx.text(StoreState.cart_total_display, color=INK, font_weight="700"), width="100%"),
                rx.text("Frete e pagamento serão calculados na próxima etapa do checkout.", color=MUTED, font_size="0.8rem", line_height="1.5"),
                rx.button("Continuar para checkout", on_click=rx.redirect("/checkout"), width="100%", background=THREAD, color=INK, border_radius="100px", font_weight="700"),
                rx.text("Seu pedido ainda não foi criado nem cobrado.", color=MUTED, font_size="0.74rem", text_align="center"),
                spacing="4", align_items="stretch", width="100%",
            ),
            background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding="1.4rem", height="fit-content",
        ),
        columns={"initial": "1", "lg": "2"}, spacing="5", width="100%", align_items="start",
    )
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.hstack(rx.vstack(
                rx.heading("Sua sacola", font_family=DISPLAY, color=INK, font_size=["2rem", "2.5rem"]),
                rx.text("Confira suas escolhas antes de continuar.", color=MUTED),
                spacing="1", align_items="flex-start",
            ), rx.spacer(), rx.link("Continuar comprando", href="/loja", color=DENIM, font_weight="700"), width="100%", align_items="center"),
            rx.cond(
                StoreState.cart_items.length() == 0,
                rx.center(rx.vstack(
                    rx.icon("shopping-bag", size=40, color=DENIM),
                    rx.heading("Sua sacola está esperando por você.", font_family=DISPLAY, color=INK, text_align="center"),
                    rx.text("Explore o catálogo e adicione seus favoritos.", color=MUTED, text_align="center"),
                    rx.link("Explorar a loja", href="/loja", background=INK, color=CHALK, padding="0.8rem 1.3rem", border_radius="100px", font_weight="700"),
                    spacing="3", align_items="center",
                ), width="100%", min_height="340px"),
                cart_content,
            ),
            spacing="5", width="100%", max_width="1160px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def device_card(device: dict) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.center(rx.icon("radio", size=24, color=DENIM), width="52px", height="52px", background="#EEF0F4", border_radius="15px"),
            rx.vstack(rx.text(device["name"], color=INK, font_weight="700"), rx.text(device["type"], color=MUTED, font_size="0.82rem"), spacing="1", align_items="flex-start"),
            rx.spacer(), rx.badge(device["status"], color_scheme=rx.cond(device["status"] == "Conectado", "green", rx.cond(device["status"] == "Pareamento pendente", "amber", "gray")), variant="soft"),
            width="100%", align="center",
        ),
        href="/dispositivo?id=" + device["id"], background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1rem", width="100%",
    )


def devices_page() -> rx.Component:
    content = rx.vstack(
        rx.cond(DeviceState.device_notice != "", rx.callout(DeviceState.device_notice, icon="info", color="amber", width="100%")),
        rx.cond(
            DeviceState.devices.length() == 0,
            rx.center(rx.vstack(
                rx.center(rx.icon("radio-tower", size=32, color=DENIM), width="72px", height="72px", background="#EEF0F4", border_radius="22px"),
                rx.heading("Seu armário ainda não tem dispositivos conectados.", font_family=DISPLAY, color=INK, text_align="center"),
                rx.text("Quando o hardware compatível estiver disponível, você poderá iniciar o pareamento seguro por aqui.", color=MUTED, text_align="center", max_width="520px", line_height="1.6"),
                rx.link("Iniciar pareamento", href="/dispositivos/conectar", background=INK, color=CHALK, padding="0.8rem 1.2rem", border_radius="100px", font_weight="700"),
                spacing="3", align="center", padding="2rem", background="#FFFFFF", border_radius="22px", width="100%",
            ), min_height="300px"),
            rx.vstack(rx.foreach(DeviceState.devices, device_card), width="100%", spacing="3", align_items="stretch"),
        ),
        spacing="4", width="100%",
    )
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.hstack(rx.vstack(rx.text("ARMÁRIO INTELIGENTE", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.15em"), rx.heading("Dispositivos", font_family=DISPLAY, color=INK, font_size=["2rem", "2.7rem"]), rx.text("Conexões reais e eventos verificados do seu armário.", color=MUTED), spacing="2", align_items="flex-start"), rx.spacer(), rx.link("+ Conectar dispositivo", href="/dispositivos/conectar", background=THREAD, color=INK, padding="0.8rem 1.1rem", border_radius="100px", font_weight="700"), width="100%", align="center", flex_wrap="wrap"),
            rx.cond(DeviceState.device_loading, rx.center(rx.spinner(size="3", color=THREAD), width="100%", min_height="220px"), rx.cond(DeviceState.device_error != "", rx.callout(DeviceState.device_error, icon="triangle_alert", color="red", width="100%"), content)),
            spacing="5", width="100%", max_width="1050px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def device_pairing_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.link("← Meus dispositivos", href="/dispositivos", color=DENIM, font_weight="700", align_self="flex-start"),
            rx.box(rx.vstack(
                rx.center(rx.icon("scan-line", size=30, color=DENIM), width="64px", height="64px", background="#EEF0F4", border_radius="20px"),
                rx.heading("Conectar um dispositivo", font_family=DISPLAY, color=INK, font_size="1.8rem"),
                rx.text("Informe o identificador exibido no dispositivo. O servidor deve emitir um código temporário de uso único.", color=MUTED, line_height="1.6"),
                field("Identificador do dispositivo", placeholder="Ex.: etiqueta ou QR code", value=DeviceState.pairing_identifier, on_change=DeviceState.set_pairing_identifier),
                rx.cond(DeviceState.pairing_error != "", rx.callout(DeviceState.pairing_error, icon="triangle_alert", color="red", width="100%")),
                rx.button(rx.cond(DeviceState.pairing_loading, "Solicitando código…", "Solicitar código de pareamento"), on_click=DeviceState.request_pairing, loading=DeviceState.pairing_loading, disabled=DeviceState.pairing_identifier == "", width="100%", background=THREAD, color=INK, border_radius="100px", font_weight="700"),
                rx.cond(DeviceState.pairing_code != "", rx.vstack(
                    rx.callout("Código temporário criado. O dispositivo só será conectado após confirmar o pareamento.", icon="shield-check", color="green", width="100%"),
                    rx.text(DeviceState.pairing_code, font_family=DISPLAY, font_size="2rem", color=INK, letter_spacing="0.14em", text_align="center", width="100%"),
                    rx.text("Expira em: " + DeviceState.pairing_expires_at, color=MUTED, font_size="0.82rem"),
                    spacing="3", width="100%", align="center", padding="1rem", background="#F7F5EF", border_radius="16px",
                )),
                rx.text("Nenhum sensor, leitura ou vínculo será criado se o serviço de pareamento não estiver disponível.", color=MUTED, font_size="0.78rem", line_height="1.5"),
                spacing="4", align="stretch", width="100%",
            ), width="100%", max_width="640px", background="#FFFFFF", padding=["1.3rem", "2rem"], border_radius="24px", border="1px solid rgba(15,26,51,0.08)"),
            spacing="4", width="100%", max_width="760px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def device_event_card(event: dict) -> rx.Component:
    return rx.hstack(
        rx.vstack(rx.text(event["kind"], color=INK, font_weight="700"), rx.text(event["created_at"], color=MUTED, font_size="0.78rem"), spacing="1", align_items="flex-start"),
        rx.spacer(), rx.text(event["value"] + " " + event["unit"], color=DENIM, font_weight="700"),
        width="100%", align="center", background="#FFFFFF", border_radius="15px", padding="1rem",
    )


def device_detail_page() -> rx.Component:
    content = rx.vstack(
        rx.hstack(rx.center(rx.icon("radio", size=25, color=DENIM), width="54px", height="54px", background="#EEF0F4", border_radius="15px"), rx.vstack(rx.heading(DeviceState.selected_device["name"], font_family=DISPLAY, color=INK, font_size="1.7rem"), rx.text(DeviceState.selected_device["type"], color=MUTED), spacing="1", align_items="flex-start"), rx.spacer(), rx.badge(DeviceState.selected_device["status"], color_scheme=rx.cond(DeviceState.selected_device["status"] == "Conectado", "green", rx.cond(DeviceState.selected_device["status"] == "Pareamento pendente", "amber", "gray")), variant="soft"), width="100%", align="center"),
        rx.hstack(rx.icon("clock-3", size=17, color=MUTED), rx.text("Último contato: " + DeviceState.selected_device["last_seen"], color=MUTED, font_size="0.86rem"), spacing="2"),
        rx.heading("Eventos recebidos", font_family=DISPLAY, color=INK, font_size="1.25rem"),
        rx.cond(DeviceState.device_events.length() == 0, rx.callout("Ainda não há eventos de hardware para mostrar.", icon="info", color="amber", width="100%"), rx.vstack(rx.foreach(DeviceState.device_events, device_event_card), width="100%", spacing="3", align_items="stretch")),
        spacing="4", width="100%", align_items="stretch", background="#FFFFFF", padding="1.5rem", border_radius="22px",
    )
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(rx.link("← Meus dispositivos", href="/dispositivos", color=DENIM, font_weight="700", align_self="flex-start"), rx.cond(DeviceState.device_loading, rx.center(rx.spinner(size="3", color=THREAD), width="100%", min_height="220px"), rx.cond(DeviceState.device_error != "", rx.callout(DeviceState.device_error, icon="triangle_alert", color="red", width="100%"), content)), spacing="4", width="100%", max_width="920px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"]), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def inspiration_card(idea: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.center(rx.icon(idea["icon"], size=46, color=DENIM), width="100%", height="170px", background="linear-gradient(145deg, #F0EDE5, #E3E8F0)", border_radius="18px"),
            rx.badge(idea["tag"], color_scheme="amber", variant="soft"),
            rx.heading(idea["title"], font_family=DISPLAY, font_size="1.28rem", color=INK),
            rx.text(idea["description"], color=MUTED, line_height="1.6", font_size="0.9rem"),
            rx.hstack(rx.link("Abrir meu armário", href="/armario", color=DENIM, font_weight="700"), rx.spacer(), rx.link("Ver a loja", href="/loja", color=DENIM), width="100%"),
            spacing="3", align_items="flex-start", width="100%",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding="1rem", width="100%",
    )


def article_card(article: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(rx.badge(article["category"], color_scheme="amber", variant="soft"), rx.spacer(), rx.text(article["reading_time"], color=MUTED, font_size="0.76rem"), width="100%"),
            rx.heading(article["title"], font_family=DISPLAY, color=INK, font_size="1.3rem", line_height="1.15"),
            rx.text(article["summary"], color=MUTED, line_height="1.6"),
            rx.link("Continuar lendo →", href="/artigo?id=" + article["id"], color=DENIM, font_weight="700"),
            spacing="3", align_items="flex-start", width="100%",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.3rem", width="100%",
    )


def challenge_card(challenge: dict) -> rx.Component:
    action = rx.cond(
        challenge["completed"] == "true",
        rx.button(rx.hstack(rx.icon("check", size=16), rx.text("Concluído"), spacing="2"), disabled=True, variant="soft", color=OK),
        rx.button("Marcar como feito", on_click=ContentState.complete_challenge(challenge["id"]), background=THREAD, color=INK, border_radius="100px", font_weight="700"),
    )
    return rx.box(
        rx.vstack(
            rx.hstack(rx.center(rx.icon(challenge["icon"], size=22, color=DENIM), width="48px", height="48px", background="#EEF0F4", border_radius="14px"), rx.spacer(), rx.badge(challenge["duration"], color_scheme="gray", variant="soft"), width="100%", align="center"),
            rx.heading(challenge["title"], font_family=DISPLAY, font_size="1.25rem", color=INK),
            rx.text(challenge["description"], color=MUTED, line_height="1.55", min_height="3rem"),
            rx.hstack(rx.text("+" + challenge["points"] + " pontos pessoais", color=DENIM, font_weight="700", font_size="0.84rem"), rx.spacer(), action, width="100%", align="center", flex_wrap="wrap"),
            spacing="3", align_items="flex-start", width="100%",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.2rem", width="100%",
    )


def inspiration_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.box(rx.vstack(rx.text("INSPIRAÇÃO", color=THREAD, font_weight="800", font_size="0.72rem", letter_spacing="0.15em"), rx.heading("Vista o seu dia.", font_family=DISPLAY, color=CHALK, font_size=["2.3rem", "3.5rem"]), rx.text("Ideias para encontrar novas combinações dentro do seu próprio armário.", color="rgba(248,249,250,0.8)", max_width="620px", line_height="1.6"), spacing="3", align_items="flex-start"), width="100%", padding=["1.5rem", "2.4rem"], background=f"linear-gradient(120deg, {INK}, {DENIM})", border_radius="24px"),
            rx.grid(rx.foreach(INSPIRATION_IDEAS, inspiration_card), columns={"initial": "1", "md": "3"}, spacing="4", width="100%"),
            rx.hstack(rx.vstack(rx.heading("Uma ideia para levar com você", font_family=DISPLAY, color=INK), rx.text("Experimente um desafio leve ou leia uma dica de cuidado.", color=MUTED), spacing="1", align_items="flex-start"), rx.spacer(), rx.link("Ver desafios", href="/desafios", background=INK, color=CHALK, padding="0.8rem 1.2rem", border_radius="100px", font_weight="700"), rx.link("Ler artigos", href="/artigos", color=DENIM, font_weight="700"), width="100%", align="center", flex_wrap="wrap"),
            spacing="5", width="100%", max_width="1180px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def articles_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.vstack(rx.text("CADERNO OSDROUPA", color=THREAD, font_weight="800", font_size="0.72rem", letter_spacing="0.15em"), rx.heading("Ideias para vestir e cuidar.", font_family=DISPLAY, color=INK, font_size=["2rem", "2.8rem"]), rx.text("Conteúdo editorial para um guarda-roupa mais pessoal e duradouro.", color=MUTED), spacing="2", align_items="flex-start", width="100%"),
            rx.grid(rx.foreach(ARTICLE_CONTENT, article_card), columns={"initial": "1", "md": "2", "lg": "3"}, spacing="4", width="100%"),
            spacing="5", width="100%", max_width="1180px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def article_detail_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.link("← Voltar aos artigos", href="/artigos", color=DENIM, font_weight="700", align_self="flex-start"),
            rx.cond(
                ContentState.article_error != "",
                rx.center(rx.vstack(rx.icon("file-question", size=38, color=DENIM), rx.heading(ContentState.article_error, font_family=DISPLAY, color=INK), rx.link("Ver artigos", href="/artigos", color=DENIM), spacing="3", align="center"), width="100%", min_height="320px"),
                rx.vstack(
                    rx.badge(ContentState.current_article["category"], color_scheme="amber", variant="soft"),
                    rx.heading(ContentState.current_article["title"], font_family=DISPLAY, color=INK, font_size=["2rem", "3rem"], line_height="1.1", max_width="860px"),
                    rx.text(ContentState.current_article["reading_time"] + " de leitura", color=MUTED, font_size="0.85rem"),
                    rx.text(ContentState.current_article["summary"], color=DENIM, font_size="1.15rem", line_height="1.6", max_width="760px"),
                    rx.text(ContentState.current_article["body"], color=INK, line_height="1.9", white_space="pre-wrap", max_width="760px"),
                    rx.link("Encontrar uma peça na loja", href="/loja", color=DENIM, font_weight="700"),
                    spacing="4", align_items="flex-start", width="100%", background="#FFFFFF", border_radius="24px", padding=["1.4rem", "2.5rem"],
                ),
            ),
            spacing="4", width="100%", max_width="1000px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def challenges_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.hstack(rx.vstack(rx.text("DESAFIOS PESSOAIS", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.15em"), rx.heading("Pequenas escolhas, novos caminhos.", font_family=DISPLAY, color=INK, font_size=["2rem", "2.7rem"]), rx.text("Atividades para redescobrir peças e cuidar do que você já tem.", color=MUTED), spacing="2", align_items="flex-start"), rx.spacer(), rx.vstack(rx.text(ContentState.challenge_points, font_family=DISPLAY, font_size="2rem", font_weight="800", color=INK), rx.text("PONTOS PESSOAIS", font_size="0.65rem", font_weight="800", color=MUTED, letter_spacing="0.1em"), spacing="0", align="center", background="#FFFFFF", border_radius="18px", padding="0.9rem 1.2rem"), width="100%", align="center", flex_wrap="wrap"),
            rx.callout("Seu progresso fica salvo neste navegador e separado por conta. A sincronização entre dispositivos ainda será integrada.", icon="info", color="amber", width="100%"),
            rx.hstack(rx.text("Progresso", color=INK, font_weight="700"), rx.spacer(), rx.text(ContentState.challenge_completion_percent.to_string() + "% concluído", color=MUTED), width="100%"),
            rx.grid(rx.foreach(ContentState.challenge_cards, challenge_card), columns={"initial": "1", "md": "2"}, spacing="4", width="100%"),
            spacing="5", width="100%", max_width="1120px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def management_navbar() -> rx.Component:
    return rx.hstack(
        rx.link(rx.hstack(rx.html(LOGO_SVG), rx.text("OSDROUPA · GESTÃO", font_family=DISPLAY, font_weight="700", color=CHALK), spacing="2", align="center"), href="/gestao"),
        rx.spacer(),
        rx.link("Visão geral", href="/gestao", color=CHALK, font_weight="600"),
        rx.link("Produtos", href="/gestao/produtos", color=CHALK, font_weight="600"),
        rx.link("Pedidos", href="/gestao/pedidos", color=CHALK, font_weight="600"),
        rx.link("Clientes", href="/gestao/clientes", color=CHALK, font_weight="600"),
        rx.link("Relatórios", href="/gestao/relatorios", color=CHALK, font_weight="600"),
        rx.link("Voltar à loja", href="/loja", color=THREAD, font_weight="700"),
        width="100%", padding_y="1rem", padding_x=["1rem", "1.5rem", "2.5rem"],
        background=INK, border_bottom="1px solid rgba(255,255,255,0.1)", position="sticky", top="0", z_index="100", spacing="4", align="center",
    )


def management_shell(title: str, subtitle: str, body: rx.Component) -> rx.Component:
    return rx.box(
        rx.el.style(CSS), management_navbar(),
        rx.center(rx.vstack(
            rx.vstack(
                rx.text("CENTRAL DE OPERAÇÕES", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.15em"),
                rx.heading(title, font_family=DISPLAY, color=INK, font_size=["2rem", "2.6rem"]),
                rx.text(subtitle, color=MUTED, line_height="1.6"),
                spacing="2", align_items="flex-start", width="100%",
            ),
            rx.cond(
                ManagementState.management_loading,
                rx.center(rx.spinner(size="3", color=THREAD), width="100%", min_height="240px"),
                rx.cond(
                    ManagementState.management_error != "",
                    rx.center(rx.vstack(
                        rx.icon(rx.cond(ManagementState.management_access_denied, "lock-keyhole", "cloud-off"), size=36, color=rx.cond(ManagementState.management_access_denied, ERROR, DENIM)),
                        rx.text(ManagementState.management_error, color=INK, text_align="center"),
                        rx.button("Tentar novamente", on_click=rx.redirect("/gestao"), variant="outline", color=DENIM),
                        rx.link("Ir para a loja", href="/loja", color=DENIM, font_weight="700"),
                        spacing="3", align_items="center", padding="2rem", background="#FFFFFF", border_radius="22px", width="100%",
                    ), width="100%", min_height="280px"),
                    body,
                ),
            ),
            spacing="5", width="100%", max_width="1220px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def management_metric_card(metric: dict) -> rx.Component:
    return rx.vstack(
        rx.text(metric["label"], color=MUTED, font_size="0.82rem", font_weight="600"),
        rx.heading(metric["value"], font_family=DISPLAY, color=INK, font_size="2rem"),
        spacing="2", align_items="flex-start", padding="1.3rem", width="100%", min_height="126px",
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px",
    )


def management_row_card(row: dict) -> rx.Component:
    return rx.hstack(
        rx.vstack(rx.text(row["name"], color=INK, font_weight="700"), rx.text("#" + row["id"], color=MUTED, font_size="0.74rem"), spacing="1", align_items="flex-start"),
        rx.spacer(), rx.badge(row["status"], color_scheme="amber", variant="soft"),
        rx.text(row["detail"], color=INK, font_weight="600"),
        width="100%", align="center", background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="16px", padding="1rem",
    )


def management_dashboard_page() -> rx.Component:
    body = rx.vstack(
        rx.grid(rx.foreach(ManagementState.management_metrics, management_metric_card), columns={"initial": "1", "sm": "2", "lg": "4"}, spacing="4", width="100%"),
        rx.grid(
            rx.link(rx.vstack(rx.icon("package", size=26, color=DENIM), rx.heading("Catálogo", font_family=DISPLAY, color=INK), rx.text("Produtos e disponibilidade", color=MUTED), spacing="2", align_items="flex-start"), href="/gestao/produtos", background="#FFFFFF", border_radius="20px", padding="1.4rem", width="100%"),
            rx.link(rx.vstack(rx.icon("clipboard-list", size=26, color=DENIM), rx.heading("Pedidos", font_family=DISPLAY, color=INK), rx.text("Fila e acompanhamento", color=MUTED), spacing="2", align_items="flex-start"), href="/gestao/pedidos", background="#FFFFFF", border_radius="20px", padding="1.4rem", width="100%"),
            rx.link(rx.vstack(rx.icon("users", size=26, color=DENIM), rx.heading("Clientes", font_family=DISPLAY, color=INK), rx.text("Contas e relacionamento", color=MUTED), spacing="2", align_items="flex-start"), href="/gestao/clientes", background="#FFFFFF", border_radius="20px", padding="1.4rem", width="100%"),
            rx.link(rx.vstack(rx.icon("chart-no-axes-combined", size=26, color=DENIM), rx.heading("Relatórios", font_family=DISPLAY, color=INK), rx.text("Indicadores agregados", color=MUTED), spacing="2", align_items="flex-start"), href="/gestao/relatorios", background="#FFFFFF", border_radius="20px", padding="1.4rem", width="100%"),
            columns={"initial": "1", "md": "2", "lg": "4"}, spacing="4", width="100%",
        ),
        spacing="5", width="100%",
    )
    return management_shell("Visão geral", "Acompanhe a operação diária do OSDROUPA.", body)


def management_list_page(title: str, subtitle: str) -> rx.Component:
    body = rx.cond(
        ManagementState.management_rows.length() == 0,
        rx.center(rx.vstack(rx.icon("inbox", size=34, color=DENIM), rx.text("Ainda não há registros para exibir.", color=MUTED), spacing="3", align_items="center"), width="100%", min_height="220px", background="#FFFFFF", border_radius="20px"),
        rx.vstack(rx.foreach(ManagementState.management_rows, management_row_card), spacing="3", width="100%", align_items="stretch"),
    )
    return management_shell(title, subtitle, body)


def management_products_page() -> rx.Component:
    return management_list_page("Catálogo e estoque", "Consulte produtos e disponibilidade.")


def management_orders_page() -> rx.Component:
    return management_list_page("Fila de pedidos", "Acompanhe os pedidos e o estado operacional.")


def management_customers_page() -> rx.Component:
    return management_list_page("Clientes", "Consulte contas atendidas pela operação.")


def management_reports_page() -> rx.Component:
    return management_list_page("Relatórios", "Indicadores agregados para apoiar decisões.")


def checkout_page() -> rx.Component:
    checkout_form = rx.grid(
        rx.vstack(
            rx.heading("Entrega", font_family=DISPLAY, color=INK, font_size="1.35rem"),
            rx.text("Escolha um endereço cadastrado na sua conta.", color=MUTED),
            rx.cond(
                OrdersState.checkout_addresses.length() > 0,
                rx.select(
                    OrdersState.checkout_address_options,
                    value=OrdersState.selected_checkout_address,
                    on_change=OrdersState.select_checkout_address,
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Você ainda não tem endereço cadastrado.", color=MUTED),
                    rx.link("Cadastrar endereço", href="/enderecos", color=DENIM, font_weight="700"),
                    align_items="flex-start", spacing="2",
                ),
            ),
            rx.divider(),
            rx.heading("Pagamento", font_family=DISPLAY, color=INK, font_size="1.35rem"),
            rx.hstack(
                rx.icon("qr-code", size=22, color=DENIM),
                rx.vstack(
                    rx.text("PIX", color=INK, font_weight="700"),
                    rx.text("O código será criado pelo Asaas após a validação do pedido.", color=MUTED, font_size="0.82rem"),
                    spacing="1", align_items="flex-start",
                ),
                align_items="center", spacing="3", width="100%",
                padding="1rem", border="1px solid rgba(15,26,51,0.12)", border_radius="16px",
            ),
            rx.cond(
                OrdersState.checkout_error != "",
                rx.callout(OrdersState.checkout_error, icon="triangle_alert", color="red", width="100%"),
            ),
            rx.cond(
                OrdersState.checkout_notice != "",
                rx.callout(OrdersState.checkout_notice, icon="info", color="amber", width="100%"),
            ),
            rx.button(
                rx.cond(OrdersState.checkout_submitting, "Validando pedido…", "Confirmar e gerar PIX"),
                on_click=OrdersState.submit_checkout,
                loading=OrdersState.checkout_submitting,
                disabled=(OrdersState.checkout_cart_count == 0) | (OrdersState.checkout_addresses.length() == 0),
                width="100%", background=THREAD, color=INK, border_radius="100px", font_weight="700",
            ),
            rx.text("Preço, estoque e total serão conferidos pelo Xano. Esta página não envia valores calculados pelo navegador.", color=MUTED, font_size="0.78rem", line_height="1.5"),
            spacing="4", align_items="stretch", width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.heading("Resumo do pedido", font_family=DISPLAY, color=INK, font_size="1.25rem"),
                rx.hstack(rx.text("Itens na sacola", color=MUTED), rx.spacer(), rx.text(OrdersState.checkout_cart_count, color=INK, font_weight="700"), width="100%"),
                rx.divider(),
                rx.text("O total final aparece depois que o servidor validar os produtos e o estoque.", color=MUTED, font_size="0.84rem", line_height="1.5"),
                rx.link("Voltar à sacola", href="/carrinho", color=DENIM, font_weight="700"),
                spacing="4", width="100%", align_items="stretch",
            ),
            background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding="1.4rem", height="fit-content",
        ),
        columns={"initial": "1", "lg": "1.5fr 1fr"}, spacing="5", width="100%", align_items="start",
    )
    success = rx.center(
        rx.vstack(
            rx.icon("circle-check", size=46, color=OK),
            rx.heading("Pedido criado · pagamento pendente", font_family=DISPLAY, color=INK, text_align="center"),
            rx.text("O pedido foi registrado. A confirmação do pagamento depende do retorno do Asaas.", color=MUTED, text_align="center"),
            rx.text("Pedido #" + OrdersState.checkout_order_id, color=INK, font_weight="700"),
            rx.cond(
                OrdersState.pix_encoded_image != "",
                rx.image(src="data:image/png;base64," + OrdersState.pix_encoded_image, alt="QR Code PIX", width="220px", height="220px"),
            ),
            rx.cond(
                OrdersState.pix_payload != "",
                rx.box(rx.text(OrdersState.pix_payload, color=INK, font_size="0.82rem", word_break="break-all"), background="#F7F5EF", border_radius="12px", padding="1rem", width="100%", max_width="600px"),
            ),
            rx.hstack(
                rx.link("Ver meus pedidos", href="/pedidos", background=INK, color=CHALK, padding="0.8rem 1.2rem", border_radius="100px", font_weight="700"),
                rx.link("Voltar à loja", href="/loja", color=DENIM, font_weight="700"),
                spacing="4", align_items="center", flex_wrap="wrap", justify="center",
            ),
            spacing="4", align_items="center", padding="2rem", background="#FFFFFF", border_radius="24px", width="100%", max_width="760px",
        ), width="100%", min_height="400px",
    )
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.link("← Voltar à sacola", href="/carrinho", color=DENIM, font_weight="700", align_self="flex-start"),
            rx.vstack(
                rx.heading("Finalizar pedido", font_family=DISPLAY, color=INK, font_size=["2rem", "2.5rem"]),
                rx.text("Entrega segura e pagamento PIX.", color=MUTED),
                spacing="1", align_items="flex-start", width="100%",
            ),
            rx.cond(OrdersState.checkout_loading, rx.center(rx.spinner(size="3", color=THREAD), width="100%", min_height="220px"), rx.cond(OrdersState.checkout_complete, success, checkout_form)),
            spacing="5", width="100%", max_width="1120px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def order_card(order: dict) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.vstack(
                rx.text("Pedido #" + order["id"], color=INK, font_weight="700"),
                rx.text(order["created_at"], color=MUTED, font_size="0.8rem"),
                spacing="1", align_items="flex-start",
            ),
            rx.spacer(),
            rx.vstack(
                rx.badge(order["status"], color_scheme="amber", variant="soft"),
                rx.text("R$ " + order["total"], color=INK, font_weight="700"),
                spacing="1", align_items="flex-end",
            ),
            width="100%", align_items="center",
        ),
        href="/pedido?id=" + order["id"],
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1.2rem", width="100%",
        _hover={"border_color": THREAD, "box_shadow": "0 8px 24px rgba(15,26,51,0.08)"},
    )


def orders_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.hstack(
                rx.vstack(rx.heading("Meus pedidos", font_family=DISPLAY, color=INK, font_size=["2rem", "2.5rem"]), rx.text("Acompanhe seus pedidos e pagamentos.", color=MUTED), spacing="1", align_items="flex-start"),
                rx.spacer(), rx.link("Continuar comprando", href="/loja", color=DENIM, font_weight="700"), width="100%", align_items="center",
            ),
            rx.cond(
                OrdersState.order_loading,
                rx.center(rx.spinner(size="3", color=THREAD), width="100%", min_height="280px"),
                rx.cond(
                    OrdersState.order_error != "",
                    rx.center(rx.vstack(rx.icon("cloud-off", size=34, color=ERROR), rx.text(OrdersState.order_error, color=INK, text_align="center"), rx.button("Tentar novamente", on_click=OrdersState.load_orders, variant="outline"), spacing="3", align_items="center"), width="100%", min_height="260px"),
                    rx.cond(
                        OrdersState.orders.length() == 0,
                        rx.center(rx.vstack(rx.icon("package-open", size=38, color=DENIM), rx.heading("Você ainda não tem pedidos.", font_family=DISPLAY, color=INK), rx.link("Conhecer a loja", href="/loja", color=DENIM, font_weight="700"), spacing="3", align_items="center"), width="100%", min_height="280px"),
                        rx.vstack(rx.foreach(OrdersState.orders, order_card), width="100%", spacing="3", align_items="stretch"),
                    ),
                ),
            ),
            spacing="5", width="100%", max_width="980px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def order_detail_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.link("← Voltar aos pedidos", href="/pedidos", color=DENIM, font_weight="700", align_self="flex-start"),
            rx.cond(
                OrdersState.order_loading,
                rx.center(rx.spinner(size="3", color=THREAD), width="100%", min_height="280px"),
                rx.cond(
                    OrdersState.order_error != "",
                    rx.center(rx.vstack(rx.icon("package-x", size=36, color=ERROR), rx.text(OrdersState.order_error, color=INK, text_align="center"), rx.link("Meus pedidos", href="/pedidos", color=DENIM), spacing="3", align_items="center"), width="100%", min_height="280px"),
                    rx.vstack(
                        rx.hstack(rx.vstack(rx.heading("Pedido #" + OrdersState.order_detail["id"], font_family=DISPLAY, color=INK, font_size="2rem"), rx.text(OrdersState.order_detail["created_at"], color=MUTED), spacing="1", align_items="flex-start"), rx.spacer(), rx.badge(OrdersState.order_detail["status"], color_scheme="amber", variant="soft"), width="100%", align_items="center"),
                        rx.divider(),
                        rx.foreach(OrdersState.order_items, lambda item: rx.hstack(rx.text(item["name"], color=INK), rx.spacer(), rx.text("Qtd. " + item["quantity"], color=MUTED), rx.text("R$ " + item["subtotal"], color=INK, font_weight="700"), width="100%", padding="0.8rem 0")),
                        rx.divider(),
                        rx.hstack(rx.text("Total", color=INK, font_weight="700"), rx.spacer(), rx.text("R$ " + OrdersState.order_detail["total"], color=INK, font_weight="700", font_size="1.2rem"), width="100%"),
                        rx.text("O status de pagamento é atualizado pelo webhook do Asaas.", color=MUTED, font_size="0.82rem"),
                        spacing="4", width="100%", align_items="stretch", background="#FFFFFF", border_radius="22px", padding="1.5rem",
                    ),
                ),
            ),
            spacing="4", width="100%", max_width="900px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


app = rx.App(
    stylesheets=[FONTS],
)
app.add_page(index, route="/", title="OSDROUPA | Guarda-Roupa Inteligente & Alfaiataria Conectada", on_load=AuthState.restore_session)
app.add_page(login_page, route="/login", title="Entrar | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(signup_page, route="/cadastro", title="Criar Conta | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(profile_page, route="/perfil", title="Meu Perfil | OSDROUPA", on_load=AuthState.require_authenticated)
app.add_page(wardrobe_page, route="/armario", title="Meu Armário | OSDROUPA", on_load=WardrobeState.load_wardrobe)
app.add_page(store_page, route="/loja", title="Loja | OSDROUPA", on_load=StoreState.load_store)
app.add_page(product_detail_page, route="/produto", title="Produto | OSDROUPA", on_load=StoreState.load_product_page)
app.add_page(cart_page, route="/carrinho", title="Minha Sacola | OSDROUPA", on_load=StoreState.load_cart_page)
app.add_page(checkout_page, route="/checkout", title="Checkout | OSDROUPA", on_load=OrdersState.load_checkout)
app.add_page(orders_page, route="/pedidos", title="Meus Pedidos | OSDROUPA", on_load=OrdersState.load_orders)
app.add_page(order_detail_page, route="/pedido", title="Detalhe do Pedido | OSDROUPA", on_load=OrdersState.load_order_detail)
app.add_page(management_dashboard_page, route="/gestao", title="Gestão | OSDROUPA", on_load=ManagementState.load_dashboard)
app.add_page(management_products_page, route="/gestao/produtos", title="Catálogo e Estoque | OSDROUPA", on_load=ManagementState.load_products)
app.add_page(management_orders_page, route="/gestao/pedidos", title="Fila de Pedidos | OSDROUPA", on_load=ManagementState.load_orders)
app.add_page(management_customers_page, route="/gestao/clientes", title="Clientes | OSDROUPA", on_load=ManagementState.load_customers)
app.add_page(management_reports_page, route="/gestao/relatorios", title="Relatórios | OSDROUPA", on_load=ManagementState.load_reports)
app.add_page(inspiration_page, route="/inspiracao", title="Inspiração | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(articles_page, route="/artigos", title="Caderno OSDROUPA | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(article_detail_page, route="/artigo", title="Artigo | OSDROUPA", on_load=ContentState.load_article)
app.add_page(challenges_page, route="/desafios", title="Desafios Pessoais | OSDROUPA", on_load=ContentState.load_challenges)
app.add_page(
    enderecos_page,
    route="/enderecos",
    title="Meus Endereços | OSDROUPA",
    on_load=AddressState.load_addresses,
)
app.add_page(
    devices_page,
    route="/dispositivos",
    title="Dispositivos do Armário | OSDROUPA",
    on_load=DeviceState.load_devices,
)
app.add_page(
    device_pairing_page,
    route="/dispositivos/conectar",
    title="Conectar Dispositivo | OSDROUPA",
    on_load=DeviceState.load_pairing_page,
)
app.add_page(
    device_detail_page,
    route="/dispositivo",
    title="Detalhe do Dispositivo | OSDROUPA",
    on_load=DeviceState.load_device_detail,
)
