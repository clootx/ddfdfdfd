import asyncio
import base64
import dataclasses
import json
import logging
import math
import os
import re
import time
import unicodedata
import uuid
import typing
from typing import Any
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from decimal import Decimal, InvalidOperation
import httpx
import reflex as rx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from OSDroupa.env import load_project_env

load_project_env()  # antes de qualquer leitura de os.environ neste módulo

from OSDroupa import daily_look  # noqa: E402
from OSDroupa.ai import imaging, limits, stylist  # noqa: E402
from OSDroupa.ai.stylist import LookPiece, LookProposal, LookReview, LookSwap  # noqa: E402

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ── Xano API ────────────────────────────────────────────────────────────────
XANO_BASE    = "https://x8ki-letl-twmt.n7.xano.io"
XANO_AUTH    = f"{XANO_BASE}/api:nqm5-KuC/auth"
XANO_PDB     = f"{XANO_BASE}/api:6LtoY7Zt"
XANO_DB      = f"{XANO_BASE}/api:EzKvuCov"
XANO_TIMEOUT = 15.0  # segundos
BACKEND_LABEL = "Xano" if os.environ.get("OSDROUPA_BACKEND", "sqlite").strip().lower() == "xano" else "SQLite local"
HOME_AFTER_AUTH = "/#como-funciona"
STORE_CATEGORIES = ("Roupas", "Calçados", "Acessórios")
DEMO_BOUTIQUES = ("Ateliê Entrelinhas", "Rua Viva Studio", "Maré de Dentro", "Forma Livre")
DEMO_COLLECTIONS = ("Alfaiataria expressiva", "Cidade em camadas", "Verão sem pressa", "Corpo em movimento")

# A instância compartilhada gratuita do Xano permite 10 chamadas por 20 s.
# Limitamos este processo a 8 para deixar margem às demais aplicações do workspace.
_XANO_WINDOW_SECONDS = 20.0
_XANO_MAX_REQUESTS_PER_WINDOW = 8


def _xano_retry_after_seconds(response: httpx.Response | None = None) -> int:
    """Read Retry-After from Xano, accepting both seconds and HTTP dates."""
    if response is not None:
        value = response.headers.get("Retry-After", "").strip()
        if value:
            try:
                return max(1, math.ceil(float(value)))
            except (ValueError, OverflowError):
                try:
                    retry_at = parsedate_to_datetime(value)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return max(
                        1,
                        math.ceil((retry_at - datetime.now(timezone.utc)).total_seconds()),
                    )
                except (TypeError, ValueError, OverflowError):
                    pass
    return int(_XANO_WINDOW_SECONDS)


def _xano_rate_limit_message(response: httpx.Response | None = None) -> str:
    seconds = _xano_retry_after_seconds(response)
    return f"O Xano limitou temporariamente as chamadas. Aguarde {seconds} segundos e tente novamente."


def _xano_failure_message(exc: BaseException, fallback: str) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, httpx.Response) and response.status_code == 429:
        return _xano_rate_limit_message(response)
    return fallback


async def _wait_for_xano_slot() -> None:
    """Enfileira chamadas entre todos os workers locais deste app."""
    from professormateria.local_backend import local_backend

    while True:
        wait_seconds = await asyncio.to_thread(
            local_backend.reserve_rate_limit_slot,
            "xano",
            _XANO_MAX_REQUESTS_PER_WINDOW,
            _XANO_WINDOW_SECONDS,
        )
        if wait_seconds <= 0:
            return
        await asyncio.sleep(max(wait_seconds, 0.05))


class XanoAsyncClient(httpx.AsyncClient):
    """Cliente HTTP que controla volume e pausa após o 429 do Xano."""

    async def request(self, method, url, *args, **kwargs):
        is_xano = str(url).startswith(XANO_BASE)
        if is_xano and os.environ.get("OSDROUPA_BACKEND", "sqlite").strip().lower() == "sqlite":
            from professormateria.local_backend import local_backend

            return await asyncio.to_thread(
                local_backend.dispatch,
                method,
                str(url),
                headers=kwargs.get("headers"),
                payload=kwargs.get("json") or {},
                params=kwargs.get("params") or {},
            )
        if is_xano:
            await _wait_for_xano_slot()

        response = await super().request(method, url, *args, **kwargs)
        if is_xano and response.status_code == 429:
            cooldown_seconds = _xano_retry_after_seconds(response)
            from professormateria.local_backend import local_backend

            await asyncio.to_thread(local_backend.pause_rate_limit, "xano", cooldown_seconds)
        return response


_PUBLIC_CATALOG_CACHE_TTL = 60.0
_SESSION_VALIDATION_CACHE_TTL = 60.0
_public_catalog_cache: dict | None = None
_public_catalog_cache_at = 0.0

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
:root {{
    color-scheme: light;
    --osd-ink: {INK};
    --osd-denim: {DENIM};
    --osd-chalk: {CHALK};
    --osd-thread: {THREAD};
    --osd-muted: {MUTED};
    --osd-radius-card: 24px;
    --osd-shadow-card: 0 18px 48px rgba(15,26,51,.075);
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html {{
    scroll-behavior: smooth;
    scroll-padding-top: 6rem;
    background: {CHALK};
}}
body {{
    width: 100%;
    overflow-x: clip;
    margin: 0;
    color: {INK};
    font-family: {BODY};
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
}}
img, svg, video {{
    max-width: 100%;
}}
::selection {{ background: rgba(233,162,59,.32); color: {INK}; }}
[id] {{
    scroll-margin-top: 6rem;
}}
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {{
    outline: 2px solid {THREAD};
    outline-offset: 4px;
    box-shadow: 0 0 0 5px rgba(233,162,59,.18);
}}
button, a {{
    transition: color 180ms ease, background-color 180ms ease, border-color 180ms ease,
                box-shadow 220ms ease, transform 220ms cubic-bezier(.2,.7,.2,1);
}}
.osd-site-header {{
    position: sticky;
    top: 0;
    z-index: 100;
    color: {CHALK};
    background: rgba(15,26,51,.94);
    border-bottom: 1px solid rgba(255,255,255,.09);
    box-shadow: 0 12px 32px rgba(6,14,31,.12);
    backdrop-filter: blur(18px) saturate(145%);
    -webkit-backdrop-filter: blur(18px) saturate(145%);
}}
.osd-header-inner {{ width: 100%; max-width: 1320px; margin: 0 auto; }}
.osd-header-primary {{ min-height: 76px; }}
.osd-header-secondary {{
    min-height: 42px;
    border-top: 1px solid rgba(255,255,255,.075);
}}
.osd-brand-mark {{ transition: transform 260ms cubic-bezier(.2,.7,.2,1); }}
.osd-brand-mark:hover {{ transform: translateY(-1px) rotate(-2deg); }}
.osd-nav-primary, .osd-nav-secondary {{
    position: relative;
    color: rgba(248,249,250,.78);
    text-decoration: none;
    white-space: nowrap;
    transition: color 180ms ease, opacity 180ms ease;
}}
.osd-nav-primary {{ font-size: .84rem; font-weight: 650; }}
.osd-nav-secondary {{ font-size: .77rem; font-weight: 600; }}
.osd-nav-primary:hover, .osd-nav-secondary:hover {{ color: {THREAD}; }}
.osd-nav-primary::after {{
    position: absolute;
    right: 0;
    bottom: -9px;
    left: 0;
    height: 2px;
    content: "";
    transform: scaleX(0);
    transform-origin: left;
    background: {THREAD};
    transition: transform 220ms cubic-bezier(.2,.7,.2,1);
}}
.osd-nav-primary:hover::after {{ transform: scaleX(1); }}
.osd-nav-pill {{
    display: inline-flex;
    align-items: center;
    min-height: 36px;
    padding: .48rem .8rem;
    color: rgba(248,249,250,.9);
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.09);
    border-radius: 999px;
    white-space: nowrap;
}}
.osd-nav-pill:hover {{ color: {THREAD}; background: rgba(255,255,255,.1); }}
.osd-motion-card {{
    transform: translateZ(0);
    transition: transform 280ms cubic-bezier(.2,.7,.2,1), box-shadow 280ms ease, border-color 220ms ease;
}}
.osd-motion-card:hover {{ transform: translateY(-5px); box-shadow: var(--osd-shadow-card); border-color: rgba(233,162,59,.34); }}
.osd-editorial-orbit {{ animation: osd-editorial-orbit 18s ease-in-out infinite alternate; }}
@keyframes osd-editorial-orbit {{
    from {{ transform: translate3d(-2%, 0, 0) rotate(-2deg); }}
    to {{ transform: translate3d(2%, 8px, 0) rotate(2deg); }}
}}
.osd-shimmer {{
    background-size: 180% 180%;
    animation: osd-shimmer 8s ease-in-out infinite;
}}
@keyframes osd-shimmer {{
    0%, 100% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
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
.osd-mobile-nav {{
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
}}
.osd-mobile-nav::-webkit-scrollbar {{
    display: none;
}}
.osd-story-reveal {{
    opacity: 1;
    transform: none;
}}
@keyframes osd-story-enter {{
    from {{ opacity: 0; transform: translate3d(0, 34px, 0); }}
    to {{ opacity: 1; transform: translate3d(0, 0, 0); }}
}}
@supports (animation-timeline: view()) {{
    .osd-story-reveal {{
        animation-name: osd-story-enter;
        animation-duration: 1ms;
        animation-timing-function: linear;
        animation-fill-mode: both;
        animation-timeline: view();
        animation-range: entry 0% entry 38%;
    }}
}}
.osd-scroll-progress {{
    position: fixed;
    top: 0;
    left: 0;
    z-index: 120;
    width: 100%;
    height: 3px;
    transform: scaleX(0);
    transform-origin: left center;
    background: {THREAD};
    pointer-events: none;
}}
@supports (animation-timeline: scroll()) {{
    .osd-scroll-progress {{
        animation: osd-page-progress auto linear both;
        animation-timeline: scroll(root block);
    }}
}}
@keyframes osd-page-progress {{
    to {{ transform: scaleX(1); }}
}}
.osd-scroll-cue {{
    animation: osd-scroll-bob 1.8s ease-in-out infinite;
}}
@keyframes osd-scroll-bob {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(5px); }}
}}
@media (prefers-reduced-motion: reduce) {{
    html {{ scroll-behavior: auto; }}
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }}
    .osd-story-reveal {{ opacity: 1 !important; transform: none !important; animation: none !important; }}
    .osd-scroll-progress {{ display: none !important; }}
    .osd-scroll-cue {{ animation: none !important; }}
    .osd-editorial-orbit, .osd-shimmer {{ animation: none !important; }}
    .osd-motion-card:hover, .osd-brand-mark:hover {{ transform: none !important; }}
}}
@media (max-width: 767px) {{
    .osd-header-primary {{ min-height: 64px; }}
    .osd-header-secondary {{ min-height: 48px; }}
}}
@media (max-width: 379px) {{
    .osd-cart-label, .osd-account-arrow, .osd-brand-caption {{ display: none !important; }}
    .osd-site-header a[href="/carrinho"] {{ padding-right: .62rem !important; padding-left: .62rem !important; }}
    .osd-header-primary {{ column-gap: .45rem !important; }}
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
    '<line x1="20" y1="30" x2="580" y2="30" stroke="#C9D3E8" stroke-width="3" stroke-linecap="round"/>'
    '<circle cx="20" cy="30" r="5" fill="#C9D3E8"/><circle cx="580" cy="30" r="5" fill="#C9D3E8"/>'
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
    forgot_password_error: bool = False
    forgot_password_link: str = ""
    reset_token: str = ""
    reset_password: str = ""
    reset_confirmation: str = ""
    reset_message: str = ""
    reset_error: bool = False

    # Autenticação
    auth_token: str = rx.Cookie(
        "",
        name="osd_auth_token",
        path="/",
        max_age=86400,
        secure=True,
        same_site="lax",
    )
    session_auth_token: str = rx.Cookie(
        "",
        name="osd_session_auth_token",
        path="/",
        secure=True,
        same_site="lax",
    )
    current_user: dict = {}
    client_profile: dict = {}
    profile_ai_personalization_draft: bool = True
    profile_name_draft: str = ""
    profile_phone_draft: str = ""
    profile_birth_date_draft: str = ""
    profile_pronouns_draft: str = ""
    profile_style_draft: str = ""
    profile_top_size_draft: str = ""
    profile_bottom_size_draft: str = ""
    profile_shoe_size_draft: str = ""
    profile_colors_draft: str = ""
    profile_bio_draft: str = ""
    profile_save_message: str = ""
    profile_save_error: bool = False
    wardrobe_items: list[dict[str, str]] = []
    wardrobe_storage: str = rx.LocalStorage("{}", name="osd_wardrobe_by_account")
    wardrobe_owner_id: str = ""
    account_validated: bool = False
    session_validated_at: float = 0.0
    session_loading: bool = False
    session_error: str = ""

    def _current_auth_token(self) -> str:
        return str(self.auth_token or self.session_auth_token or "")

    def _clear_auth_tokens(self):
        self.auth_token = ""
        self.session_auth_token = ""

    async def _session_gate(self) -> str:
        """Return ok, login, or retry so a temporary Xano error is not a logout."""
        token = self._current_auth_token()
        if not token:
            self.account_validated = False
            self.current_user = {}
            self.client_profile = {}
            self.session_error = ""
            return "login"
        if await self._sync_session(token):
            return "ok"
        return "login" if not self._current_auth_token() else "retry"

    def set_active_tab(self, tab: str):
        self.active_tab = tab
        self.login_error = ""
        self.register_error = ""
        self.forgot_password_msg = ""

    def set_login_email(self, value: str):
        self.login_email = value
        self.login_error = ""
        self.forgot_password_msg = ""

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

    def set_profile_name_draft(self, value: str):
        self.profile_name_draft = value
        self.profile_save_message = ""

    def set_profile_phone_draft(self, value: str):
        self.profile_phone_draft = value
        self.profile_save_message = ""

    def set_profile_birth_date_draft(self, value: str):
        self.profile_birth_date_draft = value
        self.profile_save_message = ""

    def set_profile_pronouns_draft(self, value: str):
        self.profile_pronouns_draft = value
        self.profile_save_message = ""

    def set_profile_style_draft(self, value: str):
        self.profile_style_draft = value
        self.profile_save_message = ""

    def set_profile_top_size_draft(self, value: str):
        self.profile_top_size_draft = value
        self.profile_save_message = ""

    def set_profile_bottom_size_draft(self, value: str):
        self.profile_bottom_size_draft = value
        self.profile_save_message = ""

    def set_profile_shoe_size_draft(self, value: str):
        self.profile_shoe_size_draft = value
        self.profile_save_message = ""

    def set_profile_colors_draft(self, value: str):
        self.profile_colors_draft = value
        self.profile_save_message = ""

    def set_profile_bio_draft(self, value: str):
        self.profile_bio_draft = value
        self.profile_save_message = ""

    def set_profile_ai_personalization_draft(self, value: bool):
        self.profile_ai_personalization_draft = bool(value)
        self.profile_save_message = ""

    async def clear_ai_feedback(self):
        """Apaga todo o histórico de 👍/👎 da conta (Change 030)."""
        if await self._session_gate() != "ok":
            self.profile_save_error = True
            self.profile_save_message = self.session_error or "Entre novamente para apagar o histórico."
            return
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.delete(f"{XANO_PDB}/feedbackLooks", headers={"Authorization": f"Bearer {self._current_auth_token()}"})
            response.raise_for_status()
            self.profile_save_error = False
            self.profile_save_message = "Histórico de avaliações dos looks apagado."
        except (httpx.HTTPError, ValueError) as exc:
            self.profile_save_error = True
            self.profile_save_message = _xano_failure_message(exc, "Não foi possível apagar o histórico agora.")

    async def save_profile(self):
        session_status = await self._session_gate()
        if session_status != "ok":
            self.profile_save_error = True
            self.profile_save_message = self.session_error or "Entre novamente para atualizar seus dados."
            return rx.redirect("/login") if session_status == "login" else None
        name = self.profile_name_draft.strip()
        phone = self.profile_phone_draft.strip()
        if len(name.split()) < 2 or len(phone) < 6:
            self.profile_save_error = True
            self.profile_save_message = "Informe nome completo e um celular válido."
            return
        if self.profile_birth_date_draft:
            try:
                birth_date = datetime.strptime(self.profile_birth_date_draft, "%Y-%m-%d").date()
            except ValueError:
                self.profile_save_error = True
                self.profile_save_message = "Informe uma data de nascimento válida."
                return
            if birth_date > datetime.now().date():
                self.profile_save_error = True
                self.profile_save_message = "A data de nascimento não pode estar no futuro."
                return
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.patch(
                    f"{XANO_PDB}/perfil",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    json={
                        "nome": name,
                        "celular": phone,
                        "data_nascimento": self.profile_birth_date_draft,
                        "pronome": self.profile_pronouns_draft,
                        "estilo_preferido": self.profile_style_draft,
                        "tamanho_superior": self.profile_top_size_draft,
                        "tamanho_inferior": self.profile_bottom_size_draft,
                        "tamanho_calcado": self.profile_shoe_size_draft,
                        "cores_favoritas": self.profile_colors_draft,
                        "sobre_mim": self.profile_bio_draft,
                        "personalizacao_ia": self.profile_ai_personalization_draft,
                    },
                )
            if response.status_code == 401:
                self._clear_auth_tokens()
                self.account_validated = False
                return rx.redirect("/login")
            response.raise_for_status()
            profile = response.json()
            if not isinstance(profile, dict):
                raise ValueError("O servidor retornou um perfil inválido.")
            self.client_profile = {**self.client_profile, **profile}
            self.current_user = {**self.current_user, "name": name}
            self.profile_save_error = False
            self.profile_save_message = "Seus dados foram atualizados."
        except (httpx.HTTPError, ValueError) as exc:
            self.profile_save_error = True
            self.profile_save_message = _xano_failure_message(exc, "Não foi possível salvar os dados agora.")

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
        return bool((self.auth_token or self.session_auth_token) and self.account_validated)

    @rx.var
    def profile_phone(self) -> str:
        return str(self.client_profile.get("celular") or "Não informado")

    @rx.var
    def account_id_label(self) -> str:
        account_id = self.current_user.get("account_id")
        return str(account_id) if account_id else "Sem conta vinculada"

    async def _sync_session(self, token: str) -> bool:
        """Valida o JWT no Xano e atualiza usuário e perfil do cliente."""
        if (
            self.account_validated
            and self.current_user.get("id")
            and time.monotonic() - self.session_validated_at < _SESSION_VALIDATION_CACHE_TTL
        ):
            return True

        self.account_validated = False
        self.session_loading = True
        self.session_error = ""
        self.current_user = {}
        self.client_profile = {}
        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                user_resp = await client.get(f"{XANO_AUTH}/me", headers=headers)
                if user_resp.status_code in (401, 403):
                    self._clear_auth_tokens()
                    self.current_user = {}
                    self.client_profile = {}
                    self.session_error = "Sua sessão expirou. Entre novamente."
                    return False
                if user_resp.status_code != 200:
                    self.session_error = (
                        _xano_rate_limit_message(user_resp)
                        if user_resp.status_code == 429
                        else "Não foi possível validar sua conta agora."
                    )
                    return False

                try:
                    user_data = user_resp.json()
                except ValueError:
                    self.session_error = "O servidor retornou uma resposta inválida ao validar sua conta."
                    return False
                if not isinstance(user_data, dict) or not user_data.get("id"):
                    self._clear_auth_tokens()
                    self.current_user = {}
                    self.client_profile = {}
                    self.session_error = "A conta não foi reconhecida. Entre novamente."
                    return False

                self.current_user = user_data
                self.account_validated = True
                self.session_validated_at = time.monotonic()

                try:
                    client_resp = await client.get(
                        f"{XANO_PDB}/buscaCliente",
                        headers=headers,
                    )
                    if client_resp.status_code == 200:
                        try:
                            profile_data = client_resp.json()
                        except ValueError:
                            profile_data = {}
                        self.client_profile = profile_data if isinstance(profile_data, dict) else {}
                    else:
                        self.client_profile = {}
                except (httpx.RequestError, ValueError):
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
        token = self._current_auth_token()
        if not token:
            self.account_validated = False
            self.current_user = {}
            self.client_profile = {}
            self.session_error = ""
            return
        await self._sync_session(token)

    async def require_authenticated(self):
        """Valida a conta no Xano e impede acesso a páginas privadas sem sessão."""
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")

    async def load_profile_page(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        if status == "ok":
            self.profile_name_draft = str(self.client_profile.get("nome") or self.current_user.get("name") or "")
            self.profile_phone_draft = str(self.client_profile.get("celular") or "")
            self.profile_birth_date_draft = str(self.client_profile.get("data_nascimento") or "")
            self.profile_pronouns_draft = str(self.client_profile.get("pronome") or "")
            self.profile_style_draft = str(self.client_profile.get("estilo_preferido") or "")
            self.profile_top_size_draft = str(self.client_profile.get("tamanho_superior") or "")
            self.profile_bottom_size_draft = str(self.client_profile.get("tamanho_inferior") or "")
            self.profile_shoe_size_draft = str(self.client_profile.get("tamanho_calcado") or "")
            self.profile_colors_draft = str(self.client_profile.get("cores_favoritas") or "")
            self.profile_bio_draft = str(self.client_profile.get("sobre_mim") or "")
            self.profile_ai_personalization_draft = self.client_profile.get("personalizacao_ia") is not False

    def validate_email(self, value: str) -> bool:
        return bool(EMAIL_RE.match(value.strip()))

    async def handle_forgot_password(self):
        self.forgot_password_msg = ""
        self.forgot_password_error = False
        self.forgot_password_link = ""
        if not self.login_email.strip() or not self.validate_email(self.login_email):
            self.forgot_password_msg = "Informe seu e-mail cadastrado acima para receber as instruções de recuperação."
            self.forgot_password_error = True
            return
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(f"{XANO_AUTH}/request-reset", json={"email": self.login_email.strip()})
            payload = response.json()
            self.forgot_password_msg = str(payload.get("message") or "Se houver uma conta para esse e-mail, as instruções serão enviadas.")
            self.forgot_password_link = str(payload.get("reset_url") or "") if response.is_success else ""
            self.forgot_password_error = not response.is_success
        except (httpx.HTTPError, ValueError) as exc:
            self.forgot_password_msg = _xano_failure_message(exc, "Não foi possível solicitar a recuperação agora.")
            self.forgot_password_error = True

    def set_reset_password(self, value: str):
        self.reset_password = value
        self.reset_message = ""

    def set_reset_confirmation(self, value: str):
        self.reset_confirmation = value
        self.reset_message = ""

    async def load_reset_page(self):
        self.reset_token = str(self.router.url.query_parameters.get("token", ""))
        self.reset_password = ""
        self.reset_confirmation = ""
        self.reset_message = ""

    async def submit_password_reset(self):
        self.reset_error = False
        self.reset_message = ""
        if not self.reset_token:
            self.reset_error = True
            self.reset_message = "O link não contém um token de recuperação. Solicite outro pelo login."
            return
        if self.reset_password != self.reset_confirmation:
            self.reset_error = True
            self.reset_message = "As senhas não conferem."
            return
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(
                    f"{XANO_AUTH}/reset-password",
                    json={"token": self.reset_token, "senha": self.reset_password},
                )
            payload = response.json()
            if response.is_success:
                self.reset_message = "Senha atualizada. Entre novamente com a nova senha."
                self.reset_token = ""
                self.reset_password = ""
                self.reset_confirmation = ""
                self._clear_auth_tokens()
                self.account_validated = False
                self.current_user = {}
                self.client_profile = {}
            else:
                self.reset_error = True
                self.reset_message = str(payload.get("message") or "O link de recuperação é inválido ou expirou.")
        except (httpx.HTTPError, ValueError) as exc:
            self.reset_error = True
            self.reset_message = _xano_failure_message(exc, "Não foi possível alterar a senha agora.")

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
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                resp = await client.post(
                    f"{XANO_AUTH}/login",
                    json={"email": self.login_email.strip(), "password": self.login_password},
                )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    self.login_error = "O servidor retornou uma resposta inválida. Tente novamente."
                    return
                if not isinstance(data, dict):
                    self.login_error = "O servidor retornou uma resposta inválida. Tente novamente."
                    return
                token = data.get("authToken", "")
                if not token:
                    self.login_error = "O servidor não retornou uma sessão válida."
                    return
                self.account_validated = False
                self.session_validated_at = 0.0
                self.current_user = {}
                self.client_profile = {}
                if self.remember_me:
                    self.auth_token = token
                    self.session_auth_token = ""
                else:
                    self.auth_token = ""
                    self.session_auth_token = token
                if not await self._sync_session(token):
                    self.login_error = self.session_error or "Não foi possível validar sua conta."
                    return
                self.login_password = ""
                return rx.redirect(HOME_AFTER_AUTH)
            else:
                if resp.status_code == 429:
                    self.login_error = _xano_rate_limit_message(resp)
                else:
                    try:
                        payload = resp.json()
                    except ValueError:
                        payload = {}
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
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                resp = await client.post(
                    f"{XANO_PDB}/cadastraCliente",
                    json={
                        "nome": self.full_name.strip(),
                        "email": self.register_email.strip(),
                        "senha": self.register_password,
                        "celular": self.phone.strip(),
                        "status": "ativo",
                        "aceitou_termos": self.accepted_terms,
                    },
                )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    self.register_error = "O servidor retornou uma resposta inválida. Tente novamente."
                    return
                if not isinstance(data, dict):
                    self.register_error = "O servidor retornou uma resposta inválida. Tente novamente."
                    return
                token = data.get("authToken")
                if not token:
                    user_data = data.get("user", {})
                    msg = user_data.get("message") if isinstance(user_data, dict) else None
                    self.register_error = msg or "Este e-mail já está cadastrado ou dados inválidos."
                    return
                self.account_validated = False
                self.session_validated_at = 0.0
                self.current_user = {}
                self.client_profile = {}
                self.auth_token = token
                self.session_auth_token = ""
                if not await self._sync_session(token):
                    self.register_error = self.session_error or "Não foi possível validar sua conta."
                    return
                self.full_name = ""
                self.register_email = ""
                self.phone = ""
                self.register_password = ""
                self.confirm_password = ""
                self.accepted_terms = False
                return rx.redirect(HOME_AFTER_AUTH)
            else:
                if resp.status_code == 429:
                    self.register_error = _xano_rate_limit_message(resp)
                else:
                    try:
                        payload = resp.json()
                    except ValueError:
                        payload = {}
                    self.register_error = payload.get("message", "Erro ao criar conta. Tente novamente.")
        except httpx.TimeoutException:
            self.register_error = "O servidor demorou para responder. Tente novamente."
        except httpx.RequestError:
            self.register_error = "Erro de conexão. Verifique sua internet e tente novamente."
        finally:
            self.is_loading = False

    def logout(self):
        """Encerra a sessão do usuário e redireciona para a página inicial."""
        self._clear_auth_tokens()
        self.current_user = {}
        self.client_profile = {}
        self.account_validated = False
        self.session_validated_at = 0.0
        self.session_error = ""
        self.login_email = ""
        self.login_password = ""
        return rx.redirect("/")

WARDROBE_CATEGORIES = ["Partes de cima", "Partes de baixo", "Vestidos", "Calçados", "Acessórios"]
WARDROBE_STATUSES = ["No armário", "Em uso", "Lavando", "Suja"]
WARDROBE_IMAGE_UPLOAD_ID = "wardrobe-item-image"
MAX_WARDROBE_IMAGE_BYTES = 2 * 1024 * 1024


class WardrobeState(AuthState):
    """Remote wardrobe with an account-partitioned local cache."""

    wardrobe_search: str = ""
    wardrobe_filter: str = "Todas"
    new_item_name: str = ""
    new_item_category: str = "Partes de cima"
    new_item_status: str = "No armário"
    new_item_color: str = ""
    new_item_season: str = ""
    new_item_size: str = ""
    new_item_brand: str = ""
    new_item_image_url: str = ""
    new_item_image_data_uri: str = ""
    new_item_purchase_price: str = ""
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
        # Fotos enviadas ficam no SQLite autenticado; não replique blobs
        # grandes no LocalStorage do navegador.
        stored[self.wardrobe_owner_id] = [
            {
                **item,
                "image_url": "" if str(item.get("image_url") or "").startswith("data:image/") else item.get("image_url", ""),
            }
            for item in self.wardrobe_items
        ]
        self.wardrobe_storage = json.dumps(stored, ensure_ascii=False)

    def _normalize_wardrobe_item(self, item: dict) -> dict[str, str]:
        local_id = str(item.get("chave_local") or item.get("local_id") or item.get("id") or uuid.uuid4().hex)
        return {
            "id": str(item.get("id") or local_id),
            "local_id": local_id,
            "name": str(item.get("nome") or item.get("name") or "Peça sem nome"),
            "category": str(item.get("categoria") or item.get("category") or WARDROBE_CATEGORIES[0]),
            "status": str(item.get("status") or "No armário"),
            "color": str(item.get("cor") or item.get("color") or ""),
            "season": str(item.get("estacao") or item.get("season") or ""),
            "size": str(item.get("tamanho") or item.get("size") or ""),
            "brand": str(item.get("marca") or item.get("brand") or ""),
            "image_url": str(item.get("imagem_url") or item.get("image_url") or ""),
            "purchase_price": str(item.get("preco_compra") or item.get("purchase_price") or ""),
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
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            return

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
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meuArmario",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                )
                if response.status_code == 401:
                    self._clear_auth_tokens()
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
                            headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                            json={
                                "chave_local": local_key,
                                "nome": local_item["name"],
                                "categoria": local_item["category"],
                                "status": local_item["status"],
                                "cor": local_item.get("color", ""),
                                "estacao": local_item.get("season", ""),
                                "tamanho": local_item.get("size", ""),
                                "marca": local_item.get("brand", ""),
                                "imagem_url": local_item.get("image_url", ""),
                                "preco_compra": local_item.get("purchase_price", ""),
                            },
                        )
                        if migration_response.status_code == 401:
                            self._clear_auth_tokens()
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
        self.pending_item_local_id = ""

    def set_new_item_category(self, value: str):
        self.new_item_category = value
        self.pending_item_local_id = ""

    def set_new_item_status(self, value: str):
        if value in WARDROBE_STATUSES:
            self.new_item_status = value
        self.pending_item_local_id = ""

    def set_new_item_color(self, value: str):
        self.new_item_color = value
        self.pending_item_local_id = ""

    def set_new_item_season(self, value: str):
        self.new_item_season = value
        self.pending_item_local_id = ""

    def set_new_item_size(self, value: str):
        self.new_item_size = value
        self.pending_item_local_id = ""

    def set_new_item_brand(self, value: str):
        self.new_item_brand = value
        self.pending_item_local_id = ""

    def set_new_item_image_url(self, value: str):
        self.new_item_image_url = value
        if value.strip():
            self.new_item_image_data_uri = ""
        self.pending_item_local_id = ""

    async def upload_new_item_image(self, files: list[rx.UploadFile]):
        if len(files) != 1:
            self.wardrobe_error = "Escolha uma foto para enviar."
            return rx.clear_selected_files(WARDROBE_IMAGE_UPLOAD_ID)
        try:
            data = await files[0].read()
        except (OSError, ValueError):
            self.wardrobe_error = "Não foi possível ler essa foto. Tente escolher o arquivo novamente."
            return rx.clear_selected_files(WARDROBE_IMAGE_UPLOAD_ID)
        if not data:
            self.wardrobe_error = "O arquivo selecionado está vazio."
            return rx.clear_selected_files(WARDROBE_IMAGE_UPLOAD_ID)
        if len(data) > MAX_WARDROBE_IMAGE_BYTES:
            self.wardrobe_error = "A foto deve ter no máximo 2 MB."
            return rx.clear_selected_files(WARDROBE_IMAGE_UPLOAD_ID)

        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"
        elif data.startswith(b"\xff\xd8\xff"):
            mime_type = "image/jpeg"
        elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            mime_type = "image/webp"
        else:
            self.wardrobe_error = "Use uma imagem JPG, PNG ou WebP válida."
            return rx.clear_selected_files(WARDROBE_IMAGE_UPLOAD_ID)

        encoded = base64.b64encode(data).decode("ascii")
        self.new_item_image_data_uri = f"data:{mime_type};base64,{encoded}"
        self.new_item_image_url = ""
        self.pending_item_local_id = ""
        self.wardrobe_error = ""
        return rx.clear_selected_files(WARDROBE_IMAGE_UPLOAD_ID)

    def set_new_item_purchase_price(self, value: str):
        self.new_item_purchase_price = value
        self.pending_item_local_id = ""

    def toggle_item_form(self):
        self.show_item_form = not self.show_item_form
        self.wardrobe_error = ""

    async def add_item(self):
        name = self.new_item_name.strip()
        category = self.new_item_category
        status = self.new_item_status
        color = self.new_item_color.strip()
        season = self.new_item_season.strip()
        size = self.new_item_size.strip()
        brand = self.new_item_brand.strip()
        image_url = self.new_item_image_url.strip()
        image_data_uri = self.new_item_image_data_uri.strip()
        purchase_price = self.new_item_purchase_price.strip()
        if not name:
            self.wardrobe_error = "Informe o nome da peça antes de salvar."
            return
        if status not in WARDROBE_STATUSES:
            self.wardrobe_error = "Escolha um estado de uso válido."
            return
        if image_url and not re.match(r"^https://[^\s]+$", image_url, re.IGNORECASE):
            self.wardrobe_error = "Use um endereço HTTPS para a foto da peça."
            return
        if image_data_uri and os.environ.get("OSDROUPA_BACKEND", "sqlite").strip().lower() != "sqlite":
            self.wardrobe_error = "O envio de arquivos está disponível no backend SQLite local. No Xano, use o link direto da imagem."
            return
        if image_data_uri and not self.wardrobe_remote_ready:
            self.wardrobe_error = "Conecte o backend local e recarregue o armário para salvar a foto na sua conta."
            return
        if not self.pending_item_local_id:
            self.pending_item_local_id = uuid.uuid4().hex
            self.pending_item_name = name
            self.pending_item_category = category
        local_id = self.pending_item_local_id
        item = {
            "id": local_id, "local_id": local_id, "name": name,
            "category": category, "status": status, "color": color, "season": season,
            "size": size, "brand": brand, "image_url": image_data_uri or image_url, "purchase_price": purchase_price, "synced": "false",
        }
        image_upload_payload = {}
        if image_data_uri:
            image_header, separator, image_base64 = image_data_uri.partition(",")
            if not separator or not image_header.startswith("data:image/") or ";base64" not in image_header:
                self.wardrobe_error = "A foto selecionada não pôde ser preparada. Envie-a novamente."
                return
            image_upload_payload = {
                "imagem_base64": image_base64,
                "imagem_mime": image_header[5:].split(";", 1)[0],
            }
        if self.wardrobe_remote_ready:
            try:
                async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                    response = await client.post(
                        f"{XANO_PDB}/meuArmario",
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                        json={
                            "chave_local": local_id,
                            "nome": name,
                            "categoria": category,
                            "status": status,
                            "cor": color,
                            "estacao": season,
                            "tamanho": size,
                            "marca": brand,
                            "imagem_url": "" if image_data_uri else image_url,
                            **image_upload_payload,
                            "preco_compra": purchase_price,
                        },
                    )
                if response.status_code == 401:
                    self._clear_auth_tokens()
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
            except (httpx.HTTPError, ValueError) as exc:
                self.wardrobe_error = _xano_failure_message(exc, "Não foi possível sincronizar a peça. Tente novamente.")
                return
        else:
            self.wardrobe_sync_notice = "Peca salva neste navegador; ainda nao sincronizada com o Xano."
        self.wardrobe_items = [item, *self.wardrobe_items]
        self._persist_wardrobe_items()
        self.new_item_name = ""
        self.new_item_status = "No armário"
        self.new_item_color = ""
        self.new_item_season = ""
        self.new_item_size = ""
        self.new_item_brand = ""
        self.new_item_image_url = ""
        self.new_item_image_data_uri = ""
        self.new_item_purchase_price = ""
        self.show_item_form = False
        self.wardrobe_error = ""
        self.pending_item_local_id = ""
        self.pending_item_name = ""
        self.pending_item_category = ""

    async def update_item_status(self, item_id: str, status: str):
        if status not in WARDROBE_STATUSES:
            return
        item = next((row for row in self.wardrobe_items if row.get("id") == str(item_id)), None)
        if not item:
            return
        if self.wardrobe_remote_ready and item.get("synced") == "true":
            try:
                async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                    response = await client.patch(
                        f"{XANO_PDB}/meuArmario/{item_id}",
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                        json={"status": status},
                    )
                if response.status_code == 401:
                    self._clear_auth_tokens()
                    self.account_validated = False
                    return rx.redirect("/login")
                response.raise_for_status()
            except httpx.HTTPError as exc:
                self.wardrobe_error = _xano_failure_message(exc, "Não foi possível sincronizar o estado de uso. Tente novamente.")
                return
        item["status"] = status
        self.wardrobe_items = list(self.wardrobe_items)
        self.wardrobe_error = ""
        self._persist_wardrobe_items()

    async def remove_item(self, item_id: str):
        item = next((row for row in self.wardrobe_items if row.get("id") == str(item_id)), None)
        if not item:
            return
        if self.wardrobe_remote_ready and item.get("synced") == "true":
            try:
                async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                    response = await client.delete(
                        f"{XANO_PDB}/meuArmario/{item_id}",
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    )
                if response.status_code == 401:
                    self._clear_auth_tokens()
                    self.account_validated = False
                    return rx.redirect("/login")
                response.raise_for_status()
            except httpx.HTTPError as exc:
                self.wardrobe_error = _xano_failure_message(exc, "Não foi possível remover a peça sincronizada.")
                return
        self.wardrobe_items = [row for row in self.wardrobe_items if row.get("id") != str(item_id)]
        self._persist_wardrobe_items()
        self.wardrobe_error = ""



# ── Estado de Gerenciamento de Endereços (AddressState) ─────────────────
LOOK_OCCASIONS = ["Dia a dia", "Trabalho", "Evento", "Viagem", "Outro"]
AI_LOOKS_FAILURE = "Não foi possível gerar os looks agora. Tente novamente em instantes."
AI_REVIEW_FAILURE = "Não foi possível avaliar o look agora. Tente novamente em instantes."
AI_IMAGE_FAILURE = "Não foi possível gerar a imagem agora. Tente novamente em instantes."


class LookState(WardrobeState):
    """Looks pessoais e agenda por conta, com sincronização remota quando disponível."""

    looks_storage: str = rx.LocalStorage("{}", name="osd_looks_by_account", sync=True)
    looks: list[dict[str, str]] = []
    selected_garment_keys: list[str] = []
    look_name: str = ""
    look_occasion: str = "Dia a dia"
    look_date: str = ""
    look_error: str = ""
    look_notice: str = ""
    looks_remote_ready: bool = False
    review_look_id: str = ""
    review_look_name: str = ""
    review_look_occasion: str = ""
    review_base_keys: list[str] = []
    look_review: LookReview = LookReview()
    review_selected_swaps: list[str] = []
    review_loading: bool = False
    review_error: str = ""

    def _read_look_store(self) -> dict[str, list[dict[str, str]]]:
        try:
            stored = json.loads(self.looks_storage or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(stored, dict):
            return {}
        return {
            str(owner): [look for look in rows if isinstance(look, dict)]
            for owner, rows in stored.items()
            if isinstance(rows, list)
        }

    def _persist_looks(self):
        if not self.wardrobe_owner_id:
            return
        stored = self._read_look_store()
        stored[self.wardrobe_owner_id] = self.looks
        self.looks_storage = json.dumps(stored, ensure_ascii=False)

    def _normalize_look(self, look: dict) -> dict[str, str]:
        keys = look.get("roupa_chaves") or look.get("garment_keys") or []
        if isinstance(keys, str):
            try:
                keys = json.loads(keys)
            except json.JSONDecodeError:
                keys = []
        if not isinstance(keys, list):
            keys = []
        return {
            "id": str(look.get("id") or look.get("chave_local") or uuid.uuid4().hex),
            "local_id": str(look.get("chave_local") or look.get("local_id") or look.get("id") or uuid.uuid4().hex),
            "name": str(look.get("nome") or look.get("name") or "Look sem nome"),
            "occasion": str(look.get("ocasiao") or look.get("occasion") or "Dia a dia"),
            "date": str(look.get("data_planejada") or look.get("date") or ""),
            "garment_keys": json.dumps([str(key) for key in keys]),
            "synced": "true" if look.get("chave_local") or look.get("synced") == "true" else "false",
        }

    @rx.var
    def garment_picker(self) -> list[dict[str, str]]:
        return [
            {**item, "selected": "true" if item["local_id"] in self.selected_garment_keys else "false"}
            for item in self.wardrobe_items
        ]

    @rx.var
    def look_cards(self) -> list[dict[str, str]]:
        cards = []
        for look in self.looks:
            try:
                keys = json.loads(look.get("garment_keys", "[]"))
            except (TypeError, json.JSONDecodeError):
                keys = []
            selected = [item for item in self.wardrobe_items if item["local_id"] in keys]
            names = [item["name"] for item in selected]
            cards.append({
                **look,
                "garment_names": ", ".join(names) if names else "As peças escolhidas não estão no armário atual.",
                "garment_count": str(len(names)),
            })
        return sorted(cards, key=lambda item: (item["date"] == "", item["date"], item["name"].casefold()))

    @rx.var
    def planned_look_cards(self) -> list[dict[str, str]]:
        return [look for look in self.look_cards if look["date"]]

    def set_look_name(self, value: str):
        self.look_name = value
        self.look_error = ""

    def set_look_occasion(self, value: str):
        if value in LOOK_OCCASIONS:
            self.look_occasion = value

    def set_look_date(self, value: str):
        self.look_date = value

    def toggle_garment(self, key: str, selected: bool):
        current = set(self.selected_garment_keys)
        if selected:
            current.add(key)
        else:
            current.discard(key)
        self.selected_garment_keys = sorted(current)
        self.look_error = ""

    async def load_looks(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            return
        await self.load_wardrobe()
        if not self.wardrobe_owner_id:
            return rx.redirect("/login")
        stored = self._read_look_store()
        cached = [self._normalize_look(look) for look in stored.get(self.wardrobe_owner_id, [])]
        self.looks = cached
        self.looks_remote_ready = False
        self.look_notice = "Looks guardados neste navegador e separados por conta."
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meusLooks",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                )
                if response.status_code == 401:
                    self._clear_auth_tokens()
                    self.account_validated = False
                    return rx.redirect("/login")
                if response.status_code == 404:
                    self.look_notice = "Sincronização dos looks ainda não publicada; seus registros locais estão preservados."
                    return
                response.raise_for_status()
                payload = response.json()
                rows = payload.get("looks", []) if isinstance(payload, dict) else payload
                if not isinstance(rows, list):
                    raise ValueError("Formato inesperado dos looks.")
                remote = [self._normalize_look(row) for row in rows if isinstance(row, dict)]
                remote_keys = {look["local_id"] for look in remote}
                unsynced = []
                migration_failed = False
                for look in cached:
                    if look["local_id"] in remote_keys:
                        continue
                    try:
                        response = await client.post(
                            f"{XANO_PDB}/meusLooks",
                            headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                            json={
                                "chave_local": look["local_id"],
                                "nome": look["name"],
                                "ocasiao": look["occasion"],
                                "data_planejada": look["date"] or None,
                                "roupa_chaves": json.loads(look["garment_keys"]),
                            },
                        )
                        if response.status_code == 401:
                            self._clear_auth_tokens()
                            self.account_validated = False
                            return rx.redirect("/login")
                        response.raise_for_status()
                        saved = response.json()
                        if isinstance(saved, dict) and isinstance(saved.get("look"), dict):
                            saved = saved["look"]
                        if not isinstance(saved, dict) or not saved.get("id"):
                            raise ValueError("Resposta inesperada ao migrar look.")
                        remote.append(self._normalize_look(saved))
                        remote_keys.add(look["local_id"])
                    except (httpx.HTTPError, ValueError):
                        migration_failed = True
                        unsynced.append(look)
                self.looks = [*remote, *unsynced]
                self.looks_remote_ready = True
                self.look_notice = "Parte dos looks continua apenas neste navegador." if migration_failed else "Looks sincronizados com sua conta."
                self._persist_looks()
        except (httpx.HTTPError, ValueError):
            self.look_notice = "Sem conexão com o Xano; exibindo looks salvos nesta conta."

    async def save_look(self):
        name = self.look_name.strip()
        valid_keys = {item["local_id"] for item in self.wardrobe_items}
        keys = sorted(set(self.selected_garment_keys) & valid_keys)
        if not name:
            self.look_error = "Dê um nome para este look."
            return
        if self.look_occasion not in LOOK_OCCASIONS:
            self.look_error = "Escolha uma ocasião válida."
            return
        if not keys:
            self.look_error = "Escolha ao menos uma peça do armário."
            return
        local_id = uuid.uuid4().hex
        look = {
            "id": local_id, "local_id": local_id, "name": name,
            "occasion": self.look_occasion, "date": self.look_date,
            "garment_keys": json.dumps(keys), "synced": "false",
        }
        if self.looks_remote_ready:
            try:
                async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                    response = await client.post(
                        f"{XANO_PDB}/meusLooks",
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                        json={
                            "chave_local": local_id,
                            "nome": name,
                            "ocasiao": self.look_occasion,
                            "data_planejada": self.look_date or None,
                            "roupa_chaves": keys,
                        },
                    )
                if response.status_code == 401:
                    self._clear_auth_tokens()
                    self.account_validated = False
                    return rx.redirect("/login")
                response.raise_for_status()
                saved = response.json()
                if isinstance(saved, dict) and isinstance(saved.get("look"), dict):
                    saved = saved["look"]
                if not isinstance(saved, dict) or not saved.get("id"):
                    raise ValueError("Resposta inesperada ao salvar look.")
                look = self._normalize_look(saved)
                self.look_notice = "Look salvo e sincronizado com sua conta."
            except (httpx.HTTPError, ValueError) as exc:
                self.look_notice = _xano_failure_message(exc, "Não foi possível sincronizar agora; o look ficou salvo neste navegador.")
        self.looks = [look, *self.looks]
        self._persist_looks()
        self.look_name = ""
        self.look_occasion = "Dia a dia"
        self.look_date = ""
        self.selected_garment_keys = []
        self.look_error = ""

    @rx.event(background=True)
    async def evaluate_look(self, look_id: str):
        """Avalia um look salvo com o provedor de IA configurado (Changes 026 e 029)."""
        owns_loading = False  # só libera o carregamento que esta chamada ligou
        try:
            async with self:
                status = await self._session_gate()
                if status == "login":
                    return rx.redirect("/login")
                if status == "retry":
                    self.review_error = self.session_error or "Não foi possível validar sua conta."
                    return
                look = next((item for item in self.looks if item["id"] == look_id), None)
                try:
                    keys = json.loads(look["garment_keys"]) if look else []
                except (TypeError, json.JSONDecodeError):
                    keys = []
                wardrobe = [dict(item) for item in self.wardrobe_items]
                pieces = stylist.closet_pieces(keys, wardrobe)
                self.review_look_id = look_id
                self.look_review = LookReview()
                self.review_selected_swaps = []
                self.review_error = ""
                if not look or not pieces:
                    self.review_error = "As peças deste look não estão mais no armário."
                    return
                if not stylist.is_configured():
                    self.review_error = "A avaliação com IA está indisponível: configure GEMINI_API_KEY no servidor."
                    return
                limit = await limits.reserve_async("texto", str(self.current_user.get("id", "")))
                if not limit.allowed:
                    self.review_error = limit.message("texto")
                    return
                self.review_loading = True
                owns_loading = True
                self.review_look_name = look["name"]
                self.review_look_occasion = look["occasion"]
                self.review_base_keys = [piece.ref for piece in pieces]
                life = await self.get_state(WardrobeLifeState)
                if not life.has_weather:
                    await life.load_weather_context()
                store = await self.get_state(StoreState)
                if not store.products:
                    await store.load_catalog()
                catalog = [dict(product) for product in store.products]
                style = str(self.client_profile.get("estilo_preferido") or "")
                context = stylist.build_prompt_context(life._weather_for_ai(), look["occasion"], style, "", wardrobe, catalog)

            try:
                raw = await stylist.request_evaluation(context, look["name"], pieces)
                review = stylist.validate_evaluation(raw, pieces, wardrobe, catalog)
            except stylist.StylistUnavailable as exc:
                if exc.reason == "quota":
                    await limits.pause_after_quota_async("texto")
                async with self:
                    self.review_error = str(exc)
                    self.review_loading = False
                return
            except Exception as exc:
                logger.warning("evaluate_look: erro inesperado (%s)", type(exc).__name__)
                async with self:
                    self.review_error = AI_REVIEW_FAILURE
                    self.review_loading = False
                return
            async with self:
                if self.review_look_id == look_id:
                    self.look_review = review
                self.review_loading = False
        except Exception as exc:
            logger.warning("evaluate_look: falha fora da chamada à IA (%s)", type(exc).__name__)
            async with self:
                self.review_error = AI_REVIEW_FAILURE
        finally:
            # Libera o carregamento em qualquer saída (sucesso, erro tratado, erro inesperado).
            if owns_loading:
                async with self:
                    self.review_loading = False

    def toggle_review_swap(self, swap_id: str):
        if swap_id in self.review_selected_swaps:
            self.review_selected_swaps = [s for s in self.review_selected_swaps if s != swap_id]
        else:
            self.review_selected_swaps = [*self.review_selected_swaps, swap_id]

    def close_review(self):
        self.review_look_id = ""
        self.look_review = LookReview()
        self.review_selected_swaps = []
        self.review_error = ""

    async def save_adjusted_look(self):
        keys = list(self.review_base_keys)
        for swap in self.look_review.trocas:
            if swap.id not in self.review_selected_swaps or swap.entra.origem != "armario":
                continue
            if swap.sai_ref in keys:
                keys[keys.index(swap.sai_ref)] = swap.entra.ref
            elif swap.entra.ref not in keys:
                keys.append(swap.entra.ref)
        if keys == self.review_base_keys:
            self.review_error = "Marque ao menos uma troca do seu armário para criar a versão ajustada."
            return
        self.look_name = f"{self.review_look_name} (ajustado)"[:80]
        self.look_occasion = self.review_look_occasion if self.review_look_occasion in LOOK_OCCASIONS else "Dia a dia"
        self.look_date = ""
        self.selected_garment_keys = keys
        await self.save_look()
        if not self.look_error:
            self.close_review()

    async def delete_look(self, look_id: str):
        look = next((row for row in self.looks if row.get("id") == str(look_id)), None)
        if not look:
            return
        if self.looks_remote_ready and look.get("synced") == "true":
            try:
                async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                    response = await client.delete(
                        f"{XANO_PDB}/meusLooks/{look_id}",
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    )
                if response.status_code == 401:
                    self._clear_auth_tokens()
                    self.account_validated = False
                    return rx.redirect("/login")
                response.raise_for_status()
            except httpx.HTTPError as exc:
                self.look_error = _xano_failure_message(exc, "Não foi possível remover o look sincronizado.")
                return
        self.looks = [row for row in self.looks if row.get("id") != str(look_id)]
        self._persist_looks()
        self.look_error = ""


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
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            return
        self.address_loading = True
        self.address_error = ""
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as c:
                r = await c.get(
                    f"{XANO_PDB}/consultaEnderecoDoCliente",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                )
            if r.status_code == 200:
                data = r.json()
                addresses = data.get("endereco1", []) if isinstance(data, dict) else None
                if not isinstance(addresses, list):
                    raise ValueError("Formato de endereços inválido.")
                self.addresses = addresses
            elif r.status_code == 429:
                self.address_error = _xano_rate_limit_message(r)
            else:
                self.address_error = "Erro ao carregar endereços."
        except httpx.TimeoutException:
            self.address_error = "Servidor demorou a responder."
        except ValueError:
            self.address_error = "O servidor retornou uma lista de endereços inválida."
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
            async with XanoAsyncClient(timeout=8.0) as c:
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
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as c:
                if self.editing_id > 0:
                    payload["endereco_id"] = self.editing_id
                    r = await c.patch(
                        f"{XANO_PDB}/atualizaEndereco",
                        json=payload,
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    )
                else:
                    r = await c.post(
                        f"{XANO_PDB}/salvaEndereco",
                        json=payload,
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    )

            if r.status_code == 200:
                self.address_success = (
                    "Endereço atualizado com sucesso!" if self.editing_id > 0
                    else "Endereço salvo com sucesso!"
                )
                self._clear_form()
                self.show_form = False
                # recarrega lista
                async with XanoAsyncClient(timeout=XANO_TIMEOUT) as c:
                    r2 = await c.get(
                        f"{XANO_PDB}/consultaEnderecoDoCliente",
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    )
                if r2.status_code == 200:
                    refreshed = r2.json()
                    addresses = refreshed.get("endereco1", []) if isinstance(refreshed, dict) else None
                    if isinstance(addresses, list):
                        self.addresses = addresses
                    else:
                        self.address_error = "O servidor retornou uma lista de endereços inválida."
                elif r2.status_code == 401:
                    self._clear_auth_tokens()
                    self.account_validated = False
                    return rx.redirect("/login")
                elif r2.status_code == 429:
                    self.address_error = _xano_rate_limit_message(r2)
            else:
                if r.status_code == 401:
                    self._clear_auth_tokens()
                    self.account_validated = False
                    return rx.redirect("/login")
                if r.status_code == 429:
                    self.address_error = _xano_rate_limit_message(r)
                else:
                    try:
                        body = r.json()
                    except ValueError:
                        body = {}
                    self.address_error = (
                        body.get("message", "Erro ao salvar endereço.")
                        if isinstance(body, dict)
                        else "Erro ao salvar endereço."
                    )
        except httpx.TimeoutException:
            self.address_error = "Servidor demorou a responder."
        except ValueError:
            self.address_error = "O servidor retornou uma resposta inválida ao salvar o endereço."
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
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as c:
                r = await c.patch(
                    f"{XANO_PDB}/marcarEnderecoPadrao",
                    json={"endereco_id": endereco_id},
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                )
            if r.status_code == 200:
                self.address_success = "Endereço padrão atualizado!"
                async with XanoAsyncClient(timeout=XANO_TIMEOUT) as c:
                    r2 = await c.get(
                        f"{XANO_PDB}/consultaEnderecoDoCliente",
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    )
                if r2.status_code == 200:
                    refreshed = r2.json()
                    addresses = refreshed.get("endereco1", []) if isinstance(refreshed, dict) else None
                    if isinstance(addresses, list):
                        self.addresses = addresses
                    else:
                        self.address_error = "O servidor retornou uma lista de endereços inválida."
                elif r2.status_code == 401:
                    self._clear_auth_tokens()
                    self.account_validated = False
                    return rx.redirect("/login")
                elif r2.status_code == 429:
                    self.address_error = _xano_rate_limit_message(r2)
            elif r.status_code == 401:
                self._clear_auth_tokens()
                self.account_validated = False
                return rx.redirect("/login")
            else:
                self.address_error = (
                    _xano_rate_limit_message(r)
                    if r.status_code == 429
                    else "Falha ao definir endereço padrão."
                )
        except httpx.TimeoutException:
            self.address_error = "Servidor demorou a responder."
        except (httpx.RequestError, ValueError):
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
    """Catálogo, lista de favoritos e sacola de compras."""

    products: list[dict[str, str]] = []
    selected_product: dict[str, str] = {}
    cart_items: list[dict[str, str]] = []
    cart_storage: str = rx.LocalStorage("[]", name="osd_store_cart", sync=True)
    favorites_storage: str = rx.LocalStorage("{}", name="osd_store_favorites_by_account", sync=True)
    favorite_product_ids: list[str] = []
    favorites_only: bool = False
    store_search: str = ""
    category_filter: str = "Todas"
    brand_filter: str = "Todas"
    collection_filter: str = "Todas"
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
        demonstration = str(item.get("demonstracao") or "").lower() in {"true", "1", "sim"}
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
            "brand": str(item.get("Marca") or item.get("marca") or item.get("brand") or "OSDROUPA"),
            "collection": str(item.get("Colecao") or item.get("colecao") or item.get("collection") or "Essenciais OSDROUPA"),
            "product_type": str(item.get("Tipo") or item.get("tipo") or item.get("product_type") or category),
            "sizes": str(item.get("Tamanhos") or item.get("tamanhos") or item.get("sizes") or "Consultar disponibilidade"),
            "colors": str(item.get("Cores") or item.get("cores") or item.get("colors") or "Consultar disponibilidade"),
            "material": str(item.get("Material") or item.get("material") or "Material a confirmar"),
            "fit": str(item.get("Caimento") or item.get("caimento") or item.get("fit") or "Consultar tabela de medidas"),
            "price": str(price),
            "price_display": _format_brl(price),
            "made_to_order": "true" if made_to_order else "false",
            "demonstration": "true" if demonstration else "false",
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
                "brand": str(item.get("brand") or "OSDROUPA"),
                "demonstration": "true" if str(item.get("demonstration") or "").lower() in {"true", "1", "sim"} else "false",
                "availability": str(item.get("availability") or "Disponibilidade a confirmar"),
                "quantity": str(quantity),
            })
        self.cart_items = cart

    def _load_favorites_from_storage(self):
        try:
            stored = json.loads(self.favorites_storage or "{}")
        except (TypeError, json.JSONDecodeError):
            stored = {}
        owner_id = str(self.current_user.get("id") or "guest")
        favorites = stored.get(owner_id, []) if isinstance(stored, dict) else []
        self.favorite_product_ids = [str(item) for item in favorites if str(item).isdigit()] if isinstance(favorites, list) else []

    def _persist_favorites(self):
        try:
            stored = json.loads(self.favorites_storage or "{}")
        except (TypeError, json.JSONDecodeError):
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        owner_id = str(self.current_user.get("id") or "guest")
        stored[owner_id] = self.favorite_product_ids
        self.favorites_storage = json.dumps(stored, ensure_ascii=False)

    def toggle_favorite(self, product_id: str):
        product_id = str(product_id)
        if product_id in self.favorite_product_ids:
            self.favorite_product_ids = [item for item in self.favorite_product_ids if item != product_id]
            self.cart_feedback = "Produto removido dos favoritos."
            favorite = "false"
        else:
            self.favorite_product_ids = [*self.favorite_product_ids, product_id]
            self.cart_feedback = "Produto salvo nos seus favoritos."
            favorite = "true"
        if self.selected_product.get("id") == product_id:
            self.selected_product = {**self.selected_product, "favorite": favorite}
        self._persist_favorites()

    def toggle_favorites_only(self):
        self.favorites_only = not self.favorites_only

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
                    "brand": product["brand"],
                    "demonstration": product["demonstration"],
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
            {**product, "favorite": "true" if product["id"] in self.favorite_product_ids else "false"}
            for product in self.products
            if (not query or any(query in product[key].casefold() for key in ("name", "description", "brand", "collection", "product_type", "colors", "material")))
            and (self.category_filter == "Todas" or product["category"] == self.category_filter)
            and (self.brand_filter == "Todas" or product["brand"] == self.brand_filter)
            and (self.collection_filter == "Todas" or product["collection"] == self.collection_filter)
            and (self.availability_filter == "Todos"
                 or product["availability"] == self.availability_filter)
            and (not self.favorites_only or product["id"] in self.favorite_product_ids)
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
    def favorite_count(self) -> int:
        return len(self.favorite_product_ids)

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

    def set_brand_filter(self, value: str):
        self.brand_filter = value

    def set_collection_filter(self, value: str):
        self.collection_filter = value

    def select_boutique(self, brand: str, collection: str):
        self.brand_filter = brand
        self.collection_filter = collection
        self.category_filter = "Todas"
        self.availability_filter = "Todos"
        self.store_search = ""
        self.favorites_only = False

    def set_price_sort(self, value: str):
        self.price_sort = value

    async def load_catalog(self):
        global _public_catalog_cache, _public_catalog_cache_at
        self.catalog_loading = True
        self.catalog_error = ""
        self.catalog_setup_required = False
        self.catalog_unclassified_count = 0

        if (
            _public_catalog_cache is not None
            and time.monotonic() - _public_catalog_cache_at < _PUBLIC_CATALOG_CACHE_TTL
        ):
            self.products = json.loads(json.dumps(_public_catalog_cache["products"]))
            self.catalog_unclassified_count = _public_catalog_cache["unclassified_count"]
            self.catalog_setup_required = _public_catalog_cache["setup_required"]
            self._sync_cart_prices()
            self.catalog_loading = False
            return

        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
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
            _public_catalog_cache = {
                "products": json.loads(json.dumps(self.products)),
                "unclassified_count": self.catalog_unclassified_count,
                "setup_required": self.catalog_setup_required,
            }
            _public_catalog_cache_at = time.monotonic()
            self._sync_cart_prices()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                self.catalog_error = _xano_rate_limit_message(exc.response)
            else:
                self.catalog_error = "Não foi possível carregar o catálogo agora. Tente novamente."
            print(f"Falha ao carregar catálogo Xano: {exc}")
        except (httpx.HTTPError, ValueError) as exc:
            self.catalog_error = _xano_failure_message(exc, "Não foi possível carregar o catálogo agora. Tente novamente.")
            print(f"Falha ao carregar catálogo Xano: {exc}")
        finally:
            self.catalog_loading = False

    async def load_store(self):
        await self.restore_session()
        self._load_cart_from_storage()
        self._load_favorites_from_storage()
        await self.load_catalog()

    async def load_product_page(self):
        await self.restore_session()
        self._load_cart_from_storage()
        self._load_favorites_from_storage()
        self.product_loading = True
        self.product_error = ""
        self.selected_product = {}
        product_id = str(self.router.url.query_parameters.get("id", ""))
        if not product_id.isdigit():
            self.product_error = "Este produto não está disponível."
            self.product_loading = False
            return
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(f"{XANO_DB}/produto/{product_id}")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("id") is None:
                raise ValueError("Produto não encontrado.")
            normalized_product = self._normalize_product(payload)
            if not normalized_product["category"]:
                raise ValueError("Produto sem categoria de vestuário.")
            normalized_product["favorite"] = "true" if normalized_product["id"] in self.favorite_product_ids else "false"
            self.selected_product = normalized_product
        except httpx.HTTPStatusError as exc:
            self.product_error = (
                _xano_rate_limit_message(exc.response)
                if exc.response.status_code == 429
                else "Não encontramos esse produto no catálogo."
            )
        except (httpx.HTTPError, ValueError) as exc:
            self.product_error = _xano_failure_message(exc, "Não encontramos esse produto no catálogo.")
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
                "brand": product["brand"],
                "demonstration": product["demonstration"],
                "availability": product["availability"],
            })
        else:
            self.cart_items = [*self.cart_items, {
                "product_id": product["id"], "name": product["name"],
                "price": product["price"], "price_display": product["price_display"],
                "image_url": product["image_url"], "category": product["category"],
                "brand": product["brand"],
                "demonstration": product["demonstration"],
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
    """Checkout demonstrativo e Checkout Pro Mercado Pago."""

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
    checkout_mode: str = "mercadopago"
    checkout_mixed_cart: bool = False
    checkout_order_id: str = ""
    checkout_url: str = ""
    orders: list[dict[str, str]] = []
    order_loading: bool = False
    order_error: str = ""
    order_detail: dict[str, str] = {"checkout_url": ""}
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

    def _refresh_checkout_mode(self):
        try:
            raw = json.loads(self.cart_storage or "[]")
        except (TypeError, json.JSONDecodeError):
            raw = []
        flags = [
            str(item.get("demonstration") or "").lower() in {"true", "1", "sim"}
            for item in raw if isinstance(item, dict) and str(item.get("product_id", "")).isdigit()
        ] if isinstance(raw, list) else []
        self.checkout_mixed_cart = any(flags) and not all(flags)
        self.checkout_mode = "demonstracao" if flags and all(flags) else "mercadopago"

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
    def checkout_display_items(self) -> list[dict[str, str]]:
        try:
            raw = json.loads(self.cart_storage or "[]")
        except (TypeError, json.JSONDecodeError):
            raw = []
        result = []
        if not isinstance(raw, list):
            return result
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                quantity = max(1, min(99, int(item.get("quantity", 1))))
                price = Decimal(str(item.get("price", "0")).replace(",", "."))
            except (TypeError, ValueError, InvalidOperation):
                continue
            result.append({
                "name": str(item.get("name") or "Produto"),
                "quantity": str(quantity),
                "unit_price": _format_brl(price),
                "line_total": _format_brl(price * quantity),
            })
        return result

    @rx.var
    def checkout_subtotal_display(self) -> str:
        try:
            raw = json.loads(self.cart_storage or "[]")
        except (TypeError, json.JSONDecodeError):
            raw = []
        total = Decimal("0")
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                try:
                    total += Decimal(str(item.get("price", "0")).replace(",", ".")) * int(item.get("quantity", 1))
                except (TypeError, ValueError, InvalidOperation):
                    continue
        return _format_brl(total)

    @rx.var
    def checkout_address_options(self) -> list[str]:
        return [f"{item['id']} · {item['label']}" for item in self.checkout_addresses]

    @rx.var
    def selected_checkout_address(self) -> str:
        match = next((item for item in self.checkout_addresses if item["id"] == self.selected_address_id), None)
        return f"{match['id']} · {match['label']}" if match else ""

    @rx.var
    def order_checkout_url(self) -> str:
        return self.order_detail.get("checkout_url", "")

    async def load_checkout(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.checkout_addresses = []
            self.checkout_error = self.session_error or "Não foi possível validar sua conta."
            return
        self.checkout_loading = True
        self.checkout_error = ""
        self.checkout_notice = ""
        self.checkout_complete = False
        self.checkout_url = ""
        self._refresh_checkout_mode()
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/consultaEnderecoDoCliente",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
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
        except (httpx.HTTPError, ValueError) as exc:
            self.checkout_error = _xano_failure_message(exc, "Não foi possível carregar seus endereços. Tente novamente.")
        finally:
            self.checkout_loading = False

    def select_checkout_address(self, value: str):
        next_address_id = value.split(" · ", 1)[0]
        if next_address_id != self.selected_address_id:
            self.selected_address_id = next_address_id
            self._ensure_idempotency_key()
        self.checkout_error = ""

    async def submit_checkout(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.checkout_error = self.session_error or "Não foi possível validar sua conta."
            return
        lines = self._cart_lines()
        self._refresh_checkout_mode()
        if self.checkout_mixed_cart:
            self.checkout_error = "Separe os produtos demonstrativos dos produtos reais antes de finalizar o pedido."
            return
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
        if self.checkout_mode == "mercadopago" and os.environ.get("OSDROUPA_BACKEND", "sqlite").strip().lower() != "sqlite":
            self.checkout_error = "Checkout Mercado Pago ainda não foi publicado no Xano. Selecione o backend SQLite para evitar chamar a integração de pagamento legada."
            return
        self._ensure_idempotency_key()
        self.checkout_submitting = True
        self.checkout_error = ""
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(
                    f"{XANO_PDB}/{'checkoutPedidoDemonstrativo' if self.checkout_mode == 'demonstracao' else 'checkoutPedido'}",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    json={
                        "endereco_id": int(self.selected_address_id),
                        "tipo": "Mercado Pago Checkout Pro",
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
            order_id = str(payload["pedido"].get("id", ""))
            if not order_id:
                self.checkout_error = "O checkout não retornou um pedido válido. A sacola e a chave da tentativa foram preservadas."
                return
            if self.checkout_mode == "demonstracao":
                self.checkout_notice = "Pedido demonstrativo enviado para confirmação da loja. Nenhum pagamento foi realizado."
            else:
                payment = payload.get("cobranca")
                if not isinstance(payment, dict):
                    raise ValueError("Cobrança ausente na resposta do checkout.")
                checkout_url = str(payment.get("checkout_url") or payload.get("checkout_url") or "")
                if not payment.get("id") or not checkout_url.startswith("https://"):
                    self.checkout_error = "O Mercado Pago não retornou um checkout seguro. A sacola e a chave da tentativa foram preservadas."
                    return
                self.checkout_url = checkout_url
                self.checkout_notice = "Pedido criado. O pagamento será confirmado somente pelo webhook do Mercado Pago."
            self.checkout_order_id = order_id
            self.checkout_complete = True
            if self.checkout_complete:
                self.cart_storage = "[]"
                self.idempotency_storage = ""
                self.idempotency_cart_storage = ""
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                self.checkout_error = "Sua sessão expirou. Entre novamente para continuar."
                self._clear_auth_tokens()
                self.account_validated = False
            elif exc.response.status_code == 429:
                self.checkout_error = _xano_rate_limit_message(exc.response)
            else:
                try:
                    detail = exc.response.json().get("message", "")
                except (ValueError, AttributeError):
                    detail = ""
                self.checkout_error = str(detail or "Não foi possível iniciar o checkout Mercado Pago. Revise os dados e tente novamente.")
        except (httpx.RequestError, ValueError):
            self.checkout_error = "Não foi possível conectar ao checkout. A chave da tentativa foi preservada para evitar duplicidade."
        finally:
            self.checkout_submitting = False

    async def load_orders(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.orders = []
            self.order_error = self.session_error or "Não foi possível validar sua conta."
            return
        self.order_loading = True
        self.order_error = ""
        self.orders = []
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meusPedidos",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                )
            if response.status_code == 404:
                self.order_error = "O histórico de pedidos ainda não está publicado no Xano."
                return
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("pedidos", []) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                raise ValueError("Formato de pedidos inválido.")
            normalized_orders = []
            for row in rows:
                if not isinstance(row, dict) or row.get("id") is None:
                    continue
                payment = row.get("pagamento") or {}
                if isinstance(payment, list):
                    payment = payment[0] if payment else {}
                payment_status = str(
                    row.get("pagamento_status")
                    or (payment.get("status_gateway") if isinstance(payment, dict) else "")
                    or "Aguardando pagamento"
                )
                normalized_orders.append({
                    "id": str(row.get("id", "")),
                    "total": str(row.get("Total", row.get("total", "0"))),
                    "status": str(row.get("status", {}).get("status") if isinstance(row.get("status"), dict) else row.get("status") or row.get("status_pedido_id") or "Em processamento"),
                    "payment_status": payment_status,
                    "paid": "true" if isinstance(payment, dict) and payment.get("pago_confirmado") else "false",
                    "created_at": str(row.get("created_at") or ""),
                })
            self.orders = normalized_orders
        except (httpx.HTTPError, ValueError) as exc:
            self.order_error = _xano_failure_message(exc, "Não foi possível carregar seus pedidos agora. Tente novamente.")
        finally:
            self.order_loading = False

    async def load_order_detail(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.order_detail = {}
            self.order_items = []
            self.order_error = self.session_error or "Não foi possível validar sua conta."
            return
        order_id = str(self.router.url.query_parameters.get("id", ""))
        self.order_detail = {}
        self.order_items = []
        self.order_error = ""
        if not order_id.isdigit():
            self.order_error = "Este pedido não foi encontrado."
            return
        self.order_loading = True
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meuPedido/{order_id}",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
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
            payment = payload.get("pagamento") or {}
            if isinstance(payment, list):
                payment = payment[0] if payment else {}
            self.order_detail = {
                "id": str(order["id"]),
                "total": str(order.get("Total", order.get("total", "0"))),
                "status": str(status.get("status") if isinstance(status, dict) else status or order.get("status_pedido_id") or "Em processamento"),
                "payment_status": str(order.get("pagamento_status") or (payment.get("status_gateway") if isinstance(payment, dict) else "") or "Aguardando pagamento"),
                "paid": "true" if isinstance(payment, dict) and payment.get("pago_confirmado") else "false",
                "created_at": str(order.get("created_at") or ""),
                "checkout_url": str(order.get("checkout_url") or ""),
            }
            raw_items = payload.get("itens", []) if isinstance(payload, dict) else []
            if isinstance(raw_items, list):
                self.order_items = [{
                    "name": str(item.get("produto", {}).get("Nome") if isinstance(item.get("produto"), dict) else item.get("Nome") or f"Produto {item.get('produto_id', '')}"),
                    "quantity": str(item.get("Qtd", item.get("qtd", "1"))),
                    "subtotal": str(item.get("Subtotal", item.get("subtotal", "0"))),
                } for item in raw_items if isinstance(item, dict)]
        except (httpx.HTTPError, ValueError) as exc:
            self.order_error = _xano_failure_message(exc, "Não foi possível carregar este pedido.")
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
    {"id": "repeat-three", "title": "Três dias, uma peça favorita", "description": "Use a mesma peça em três combinações diferentes nesta semana.", "points": "30", "duration": "7 dias", "icon": "repeat-2", "category": "Looks", "action_label": "Montar um look", "action_href": "/look-do-dia"},
    {"id": "forgotten-piece", "title": "Resgate uma peça esquecida", "description": "Escolha algo pouco usado no armário e monte um look em volta dessa peça.", "points": "40", "duration": "15 min", "icon": "sparkles", "category": "Armário", "action_label": "Abrir meu armário", "action_href": "/armario"},
    {"id": "care-routine", "title": "Um cuidado que faz diferença", "description": "Confira a etiqueta e cuide de uma peça que precisa de atenção.", "points": "20", "duration": "Hoje", "icon": "heart-handshake", "category": "Cuidado", "action_label": "Ver peças e usos", "action_href": "/historico-uso"},
    {"id": "plan-week", "title": "Planeje três combinações", "description": "Deixe três ideias prontas para os próximos dias usando seu acervo.", "points": "25", "duration": "20 min", "icon": "calendar-check-2", "category": "Planejamento", "action_label": "Planejar combinações", "action_href": "/calendario"},
    {"id": "repair-one", "title": "Dê um novo ponto a uma peça", "description": "Identifique uma peça que merece reparo e descreva o ajuste necessário.", "points": "15", "duration": "10 min", "icon": "scissors", "category": "Cuidado", "action_label": "Conhecer a alfaiataria", "action_href": "/servicos"},
    {"id": "color-repeat", "title": "Repita uma cor com intenção", "description": "Crie duas combinações diferentes usando uma cor que já existe no seu armário.", "points": "20", "duration": "15 min", "icon": "palette", "category": "Looks", "action_label": "Encontrar combinações", "action_href": "/look-do-dia"},
    {"id": "wear-log", "title": "Registre três usos", "description": "Anote três ocasiões em que você usou peças que já tem.", "points": "20", "duration": "Esta semana", "icon": "clipboard-check", "category": "Armário", "action_label": "Registrar um uso", "action_href": "/historico-uso"},
    {"id": "closet-review", "title": "Revise cinco peças", "description": "Atualize o estado de cinco itens para deixar seu armário digital em dia.", "points": "25", "duration": "10 min", "icon": "list-checks", "category": "Armário", "action_label": "Organizar armário", "action_href": "/armario"},
]


class ContentState(AuthState):
    challenge_storage: str = rx.LocalStorage("{}", name="osd_challenges_by_account", sync=True)
    completed_challenges: list[str] = []
    challenge_category_filter: str = "Todas"
    challenge_status_filter: str = "Todos"
    challenge_sync_message: str = "Carregando seu progresso..."
    current_article: dict[str, str] = {}
    article_error: str = ""

    @rx.var
    def challenge_cards(self) -> list[dict[str, str]]:
        completed = set(self.completed_challenges)
        return [{**item, "completed": "true" if item["id"] in completed else "false"} for item in WARDROBE_CHALLENGES]

    @rx.var
    def filtered_challenge_cards(self) -> list[dict[str, str]]:
        completed = set(self.completed_challenges)
        cards = [{**item, "completed": "true" if item["id"] in completed else "false"} for item in WARDROBE_CHALLENGES]
        if self.challenge_category_filter != "Todas":
            cards = [item for item in cards if item["category"] == self.challenge_category_filter]
        if self.challenge_status_filter == "Em aberto":
            cards = [item for item in cards if item["completed"] == "false"]
        elif self.challenge_status_filter == "Concluídos":
            cards = [item for item in cards if item["completed"] == "true"]
        return cards

    @rx.var
    def challenge_points(self) -> int:
        points_by_id = {item["id"]: int(item["points"]) for item in WARDROBE_CHALLENGES}
        return sum(points_by_id.get(item_id, 0) for item_id in self.completed_challenges)

    @rx.var
    def challenge_completion_percent(self) -> int:
        return int(len(self.completed_challenges) / max(1, len(WARDROBE_CHALLENGES)) * 100)

    def set_challenge_category_filter(self, value: str):
        self.challenge_category_filter = value

    def set_challenge_status_filter(self, value: str):
        self.challenge_status_filter = value

    def reset_challenge_filters(self):
        self.challenge_category_filter = "Todas"
        self.challenge_status_filter = "Todos"

    async def load_challenges(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.completed_challenges = []
            self.challenge_sync_message = self.session_error or "Não foi possível validar sua conta."
            return
        owner_id = str(self.current_user.get("id", ""))
        try:
            stored = json.loads(self.challenge_storage or "{}")
        except (TypeError, json.JSONDecodeError):
            stored = {}
        progress = stored.get(owner_id, []) if isinstance(stored, dict) else []
        valid_ids = {challenge["id"] for challenge in WARDROBE_CHALLENGES}
        self.completed_challenges = [item for item in progress if isinstance(item, str) and item in valid_ids]
        local_progress = list(self.completed_challenges)
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meusDesafios",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                )
            if response.status_code == 401:
                self._clear_auth_tokens()
                self.account_validated = False
                return rx.redirect("/login")
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("concluidos", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list):
                raise ValueError("Formato inesperado de desafios.")
            remote_ids = set(
                str(row.get("desafio_id"))
                for row in rows
                if isinstance(row, dict) and row.get("desafio_id") in valid_ids
            )
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                for challenge_id in local_progress:
                    if challenge_id in remote_ids:
                        continue
                    migration = await client.post(
                        f"{XANO_PDB}/concluirDesafio",
                        headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                        json={"desafio_id": challenge_id},
                    )
                    if migration.status_code == 401:
                        self._clear_auth_tokens()
                        self.account_validated = False
                        return rx.redirect("/login")
                    migration.raise_for_status()
                    remote_ids.add(challenge_id)
            self.completed_challenges = [
                challenge["id"]
                for challenge in WARDROBE_CHALLENGES
                if challenge["id"] in remote_ids
            ]
            if not isinstance(stored, dict):
                stored = {}
            stored[owner_id] = self.completed_challenges
            self.challenge_storage = json.dumps(stored, ensure_ascii=False)
            self.challenge_sync_message = "Progresso sincronizado com sua conta."
        except (httpx.HTTPError, ValueError):
            self.challenge_sync_message = "Progresso salvo neste navegador; a sincronização está indisponível."

    async def complete_challenge(self, challenge_id: str):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.completed_challenges = []
            self.challenge_sync_message = self.session_error or "Não foi possível validar sua conta."
            return
        if challenge_id not in {item["id"] for item in WARDROBE_CHALLENGES}:
            return
        if challenge_id in self.completed_challenges:
            return
        synced = False
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(
                    f"{XANO_PDB}/concluirDesafio",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    json={"desafio_id": challenge_id},
                )
            if response.status_code == 401:
                self._clear_auth_tokens()
                self.account_validated = False
                return rx.redirect("/login")
            response.raise_for_status()
            synced = True
        except httpx.HTTPError:
            synced = False
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
        self.challenge_sync_message = (
            "Desafio sincronizado com sua conta."
            if synced
            else "Desafio salvo neste navegador; será sincronizado quando o Xano estiver disponível."
        )

    async def load_article(self):
        await self.restore_session()
        article_id = str(self.router.url.query_parameters.get("id", ""))
        self.article_error = ""
        self.current_article = next((article for article in ARTICLE_CONTENT if article["id"] == article_id), {})
        if not self.current_article:
            self.article_error = "Não encontramos esse artigo."


class WardrobeLifeState(WardrobeState):
    """Personal wardrobe journeys: daily looks, travel, usage, trust and services."""

    experience_error: str = ""
    experience_notice: str = ""
    daily_weather: str = "Ameno"
    daily_occasion: str = "Dia a dia"
    weather_context: dict[str, str] = {}
    weather_city_query: str = ""
    weather_loading: bool = False
    weather_notice: str = ""
    ai_proposals: list[LookProposal] = []
    ai_note: str = ""
    ai_loading: bool = False
    ai_notice: str = ""
    ai_error: str = ""
    image_loading_id: str = ""
    ai_saved_inspirations: list[str] = []
    ai_feedback: dict[str, str] = {}
    ai_feedback_open_id: str = ""
    daily_suggestions: list[dict[str, str]] = []
    experience_loading: bool = False
    history_items: list[dict[str, str]] = []
    wear_events: list[dict[str, str]] = []
    selected_wear_item: str = ""
    wear_occasion: str = "Dia a dia"
    loyalty_points: int = 0
    loyalty_level: str = "Começo"
    loyalty_next_level: str = "Fio"
    loyalty_points_to_next: int = 25
    loyalty_tier_progress: int = 0
    loyalty_completed: int = 0
    loyalty_challenge_total: int = 0
    loyalty_history: list[dict[str, str]] = []
    packing_name: str = ""
    packing_destination: str = ""
    packing_start: str = ""
    packing_end: str = ""
    packing_occasion: str = "Viagem"
    packing_selected_ids: list[str] = []
    packing_plans: list[dict[str, str]] = []
    tryon_selected_ids: list[str] = []
    testimonial_text: str = ""
    testimonial_anonymous: bool = False
    testimonial_consent: bool = False
    testimonials: list[dict[str, str]] = []
    my_testimonials: list[dict[str, str]] = []
    tailoring_service: str = "Ajuste de caimento"
    tailoring_garment: str = ""
    tailoring_notes: str = ""
    tailoring_date: str = ""
    tailoring_requests: list[dict[str, str]] = []
    privacy_request_type: str = "Acesso aos dados"
    privacy_details: str = ""
    privacy_requests: list[dict[str, str]] = []
    admin_testimonials: list[dict[str, str]] = []
    admin_privacy_requests: list[dict[str, str]] = []
    admin_tailoring_requests: list[dict[str, str]] = []

    @staticmethod
    def _string_rows(rows: Any) -> list[dict[str, str]]:
        if not isinstance(rows, list):
            return []
        return [
            {str(key): "" if value is None else str(value) for key, value in row.items()}
            for row in rows
            if isinstance(row, dict)
        ]

    @rx.var
    def tryon_items(self) -> list[dict[str, str]]:
        return [item for item in self.wardrobe_items if item["local_id"] in self.tryon_selected_ids]

    @rx.var
    def tryon_item_cards(self) -> list[dict[str, str]]:
        return [
            {**item, "selected": "true" if item["local_id"] in self.tryon_selected_ids else "false"}
            for item in self.wardrobe_items
        ]

    @rx.var
    def packing_item_cards(self) -> list[dict[str, str]]:
        return [
            {**item, "selected": "true" if item["id"] in self.packing_selected_ids else "false"}
            for item in self.wardrobe_items
        ]

    async def _life_request(self, method: str, endpoint: str, *, payload: dict | None = None, params: dict | None = None):
        async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
            return await client.request(
                method,
                f"{XANO_PDB}/{endpoint}",
                headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                json=payload,
                params=params,
            )

    async def load_daily_look(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        if status == "retry":
            self.experience_error = self.session_error or "Não foi possível validar sua conta."
            return
        await self.load_wardrobe()
        self.experience_loading = True
        self.experience_error = ""
        try:
            response = await self._life_request("GET", "lookDoDia", params={"clima": self.daily_weather, "ocasiao": self.daily_occasion})
            response.raise_for_status()
            data = response.json()
            rows = data.get("pecas", []) if isinstance(data, dict) else []
            self.daily_suggestions = [self._normalize_wardrobe_item(item) for item in rows if isinstance(item, dict)]
            if not self.daily_suggestions:
                self.experience_notice = "Adicione algumas peças ao armário para montar sua primeira combinação."
            else:
                self.experience_notice = f"Sugestão para {self.daily_occasion.lower()} · clima {self.daily_weather.lower()}."
        except (httpx.HTTPError, ValueError) as exc:
            # Plano B: mesma regra do endpoint calculada aqui, só quando o lookDoDia falha.
            logger.warning("lookDoDia indisponível (%s: %s); usando a regra local", type(exc).__name__, exc)
            self.daily_suggestions = daily_look.pick_daily_look(self.wardrobe_items, self.daily_weather, self.daily_occasion)
            if self.daily_suggestions:
                self.experience_notice = f"Sugestão calculada localmente porque {daily_look.failure_reason(exc)}."
            else:
                self.experience_error = _xano_failure_message(exc, "Não foi possível buscar uma combinação agora.")
        finally:
            self.experience_loading = False

    def set_daily_weather(self, value: str):
        if value in {"Quente", "Ameno", "Frio", "Chuvoso"}:
            self.daily_weather = value
            if self.weather_context and value != self.weather_context.get("categoria"):
                self.weather_context = {**self.weather_context, "manual": "1"}
                self.weather_notice = "Clima escolhido manualmente; a previsão continua visível como referência."

    def set_weather_city_query(self, value: str):
        self.weather_city_query = value[:80]

    @rx.var
    def has_weather(self) -> bool:
        return bool(self.weather_context.get("cidade"))

    def set_ai_note(self, value: str):
        self.ai_note = value[:stylist.MAX_NOTE_LENGTH]

    def _weather_for_ai(self) -> dict:
        if self.weather_context.get("cidade") and not self.weather_context.get("manual"):
            return dict(self.weather_context)
        return {"categoria": self.daily_weather, "observacao": "clima escolhido manualmente pela pessoa"}

    async def _saved_looks_for_ai(self) -> list[dict]:
        """Looks salvos mais recentes, para a IA não repetir; falha aqui não impede a geração."""
        try:
            response = await self._life_request("GET", "meusLooks")
            response.raise_for_status()
            data = response.json()
            rows = data.get("looks", []) if isinstance(data, dict) else data
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("meusLooks indisponível para a IA (%s)", type(exc).__name__)
            return []
        if not isinstance(rows, list):
            return []
        rows = [row for row in rows if isinstance(row, dict)]
        return sorted(rows, key=lambda row: str(row.get("created_at") or ""), reverse=True)[:stylist.MAX_RECENT_LOOKS]

    async def _optional_rows(self, endpoint: str, key: str) -> list[dict]:
        """Lista auxiliar para a personalização; indisponível vira lista vazia."""
        try:
            response = await self._life_request("GET", endpoint)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("%s indisponível para a personalização (%s)", endpoint, type(exc).__name__)
            return []
        rows = data.get(key, []) if isinstance(data, dict) else []
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

    @rx.var
    def ai_personalization_on(self) -> bool:
        return self.client_profile.get("personalizacao_ia") is not False

    def open_ai_feedback(self, proposal_id: str):
        self.ai_feedback_open_id = "" if self.ai_feedback_open_id == proposal_id else proposal_id

    async def send_ai_feedback(self, proposal_id: str, rating: str, reason: str = ""):
        """Grava 👍/👎 só quando a pessoa clica (Change 030)."""
        proposal = next((p for p in self.ai_proposals if p.id == proposal_id), None)
        if proposal is None or rating not in ("positivo", "negativo") or not self.ai_personalization_on:
            return
        try:
            response = await self._life_request("POST", "feedbackLooks", payload={
                "nome": proposal.nome,
                "roupa_chaves": [piece.ref for piece in proposal.pecas if piece.origem == "armario"],
                "avaliacao": rating, "motivo": reason,
                "ocasiao": self.daily_occasion, "clima": self.daily_weather,
            })
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            self.ai_error = _xano_failure_message(exc, "Não foi possível registrar sua avaliação agora.")
            return
        self.ai_feedback = {**self.ai_feedback, proposal_id: rating}
        self.ai_feedback_open_id = ""
        self.ai_notice = "Obrigado! Sua avaliação vai orientar as próximas sugestões."

    async def _use_heuristic_look(self, reason: str):
        await self.load_daily_look()
        self.ai_proposals = [stylist.heuristic_proposal(self.daily_suggestions, self.daily_occasion, self.daily_weather)] if self.daily_suggestions else []
        self.ai_notice = f"Sugestão básica (IA indisponível). {reason}".strip()

    @rx.event(background=True)
    async def generate_ai_looks(self):
        """Gera looks com o provedor de IA (Gemini) no servidor; usa a heurística atual como alternativa (Change 025)."""
        owns_loading = False  # só libera o carregamento que esta chamada ligou
        try:
            async with self:
                status = await self._session_gate()
                if status == "login":
                    return rx.redirect("/login")
                if status == "retry":
                    self.ai_error = self.session_error or "Não foi possível validar sua conta."
                    return
                self.ai_loading = True
                owns_loading = True
                self.ai_error = ""
                self.ai_notice = ""
                await self.load_wardrobe()
                wardrobe = [dict(item) for item in self.wardrobe_items]
                account_id = str(self.current_user.get("id", ""))
                style = str(self.client_profile.get("estilo_preferido") or "")
                if not stylist.is_configured():
                    await self._use_heuristic_look("Configure GEMINI_API_KEY para ativar o estilista com IA.")
                    self.ai_loading = False
                    return
                limit = await limits.reserve_async("texto", account_id)
                if not limit.allowed:
                    self.ai_error = limit.message("texto")
                    self.ai_loading = False
                    return
                store = await self.get_state(StoreState)
                if not store.products:
                    await store.load_catalog()
                catalog = [dict(product) for product in store.products]
                recent = stylist.recent_looks(await self._saved_looks_for_ai(), self.ai_proposals, wardrobe)
                style_profile = None
                if self.ai_personalization_on:
                    usage = await self._optional_rows("historicoUso", "itens")
                    feedback = await self._optional_rows("feedbackLooks", "feedbacks")
                    style_profile = stylist.build_style_profile(str(self.client_profile.get("cores_favoritas") or ""), usage, feedback, wardrobe)
                else:
                    style = ""  # personalização desligada no perfil: nada de gosto pessoal no contexto
                context = stylist.build_prompt_context(self._weather_for_ai(), self.daily_occasion, style, self.ai_note, wardrobe, catalog, recent, style_profile)

            try:
                proposals, _ = stylist.validate_looks(await stylist.request_looks(context), wardrobe, catalog, recent)
                if not proposals:
                    raise stylist.StylistUnavailable("A IA de estilo não montou nenhuma combinação válida.")
            except stylist.StylistUnavailable as exc:
                if exc.reason == "quota":
                    await limits.pause_after_quota_async("texto")
                async with self:
                    await self._use_heuristic_look(str(exc))
                    self.ai_loading = False
                return
            except Exception as exc:
                logger.warning("generate_ai_looks: erro inesperado (%s)", type(exc).__name__)
                async with self:
                    await self._use_heuristic_look("A IA de estilo está indisponível no momento.")
                    self.ai_loading = False
                return

            async with self:
                self.ai_proposals = proposals
                self.ai_notice = f"{len(proposals)} looks criados pela IA para {self.daily_occasion.lower()}."
                self.ai_loading = False
        except Exception as exc:
            logger.warning("generate_ai_looks: falha fora da chamada à IA (%s)", type(exc).__name__)
            async with self:
                self.ai_error = AI_LOOKS_FAILURE
        finally:
            # Libera o carregamento em qualquer saída (sucesso, erro tratado, erro inesperado).
            if owns_loading:
                async with self:
                    self.ai_loading = False

    @rx.var
    def image_ai_enabled(self) -> bool:
        return imaging.is_configured()

    @rx.event(background=True)
    async def generate_look_image(self, proposal_id: str):
        """Gera a imagem editorial do look com a API Gemini do Google (Change 027)."""
        owns_loading = False  # só libera o carregamento que esta chamada ligou
        try:
            async with self:
                if self.image_loading_id:
                    return
                proposal = next((p for p in self.ai_proposals if p.id == proposal_id), None)
                if proposal is None:
                    return
                if not imaging.is_configured():
                    self.ai_error = "A geração de imagens está indisponível: ative OSDROUPA_IMAGES_ENABLED e configure GEMINI_API_KEY no servidor."
                    return
                account_id = str(self.current_user.get("id", ""))
                limit = await limits.reserve_async("imagem", account_id)
                if not limit.allowed:
                    self.ai_error = limit.message("imagem")
                    return
                self.image_loading_id = proposal_id
                owns_loading = True
                self.ai_error = ""
                pieces = [{"papel": p.papel_label, "nome": p.nome, "descricao": p.descricao, "imagem_url": p.imagem_url} for p in proposal.pecas]
                look_name, palette, fabrics = proposal.nome, proposal.paleta, proposal.tecidos

            try:
                filename = await imaging.generate_look_image(look_name, pieces, palette, fabrics, rx.get_upload_dir() / "looks")
            except imaging.ImageUnavailable as exc:
                if exc.reason == "quota":
                    await limits.pause_after_quota_async("imagem")
                async with self:
                    self.ai_error = str(exc)
                    self.image_loading_id = ""
                return
            except Exception as exc:
                logger.warning("generate_look_image: erro inesperado (%s)", type(exc).__name__)
                async with self:
                    self.ai_error = AI_IMAGE_FAILURE
                    self.image_loading_id = ""
                return
            async with self:
                proposals = list(self.ai_proposals)
                for item in proposals:
                    if item.id == proposal_id:
                        item.imagem_gerada = f"looks/{filename}"
                self.ai_proposals = proposals
                self.image_loading_id = ""
        except Exception as exc:
            logger.warning("generate_look_image: falha fora da chamada à IA (%s)", type(exc).__name__)
            async with self:
                self.ai_error = AI_IMAGE_FAILURE
        finally:
            # Libera o carregamento em qualquer saída (sucesso, erro tratado, erro inesperado).
            if owns_loading:
                async with self:
                    self.image_loading_id = ""

    async def save_ai_inspiration(self, proposal_id: str):
        """Guarda a proposta (com imagem e avaliação) nas inspirações da conta (Change 028)."""
        proposal = next((p for p in self.ai_proposals if p.id == proposal_id), None)
        if proposal is None or proposal_id in self.ai_saved_inspirations:
            return
        weather = self.weather_context if self.weather_context.get("cidade") else {}
        rationale = " ".join(x for x in [proposal.justificativa_clima, proposal.justificativa_estilo] if x)
        payload = {
            "chave_local": proposal.id,
            "nome": proposal.nome,
            "ocasiao": self.daily_occasion,
            "clima": self.daily_weather,
            "regiao": weather.get("regiao", ""),
            "estacao": weather.get("estacao", ""),
            "paleta": proposal.paleta,
            "tecidos": proposal.tecidos,
            "justificativa": rationale,
            "nota": proposal.avaliacao.nota_geral,
            "imagem": proposal.imagem_gerada,
            # Fotos do armário são privadas: só imagens do catálogo seguem com as peças.
            "pecas": [
                {"papel": p.papel_label, "nome": p.nome, "descricao": p.descricao, "origem": p.origem,
                 "imagem_url": p.imagem_url if p.origem == "catalogo" else ""}
                for p in proposal.pecas
            ],
        }
        try:
            response = await self._life_request("POST", "minhasInspiracoes", payload=payload)
            response.raise_for_status()
            self.ai_saved_inspirations = [*self.ai_saved_inspirations, proposal_id]
            self.ai_notice = f"“{proposal.nome}” foi guardado nas suas inspirações."
            self.ai_error = ""
        except (httpx.HTTPError, ValueError) as exc:
            self.ai_error = _xano_failure_message(exc, "Não foi possível guardar esta inspiração agora.")

    def apply_ai_swap(self, proposal_id: str, swap_id: str):
        proposals = list(self.ai_proposals)
        proposal = next((p for p in proposals if p.id == proposal_id), None)
        if proposal and stylist.apply_swap(proposal, swap_id):
            self.ai_proposals = proposals
            self.ai_notice = f"Troca aplicada em “{proposal.nome}”."

    async def save_ai_proposal(self, proposal_id: str):
        proposal = next((p for p in self.ai_proposals if p.id == proposal_id), None)
        closet_keys = [piece.ref for piece in (proposal.pecas if proposal else []) if piece.origem == "armario"]
        if not closet_keys:
            self.ai_error = "Este look não tem peças do seu armário para salvar."
            return
        try:
            response = await self._life_request("POST", "meusLooks", payload={
                "chave_local": uuid.uuid4().hex,
                "nome": proposal.nome,
                "ocasiao": self.daily_occasion,
                "data_planejada": datetime.now(timezone.utc).date().isoformat(),
                "roupa_chaves": closet_keys,
            })
            response.raise_for_status()
            self.ai_notice = f"“{proposal.nome}” foi salvo em Meus Looks."
            self.ai_error = ""
        except (httpx.HTTPError, ValueError) as exc:
            self.ai_error = _xano_failure_message(exc, "Não foi possível salvar este look agora.")

    async def _default_address_city(self) -> tuple[str, str]:
        response = await self._life_request("GET", "consultaEnderecoDoCliente")
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("endereco1", []) if isinstance(payload, dict) else []
        rows = [row for row in rows if isinstance(row, dict)]
        address = next((row for row in rows if row.get("padrao")), rows[0] if rows else None)
        cep = (address or {}).get("_cep") or {}
        return str(cep.get("cidade") or "").strip(), str(cep.get("uf") or "").strip().upper()

    async def _apply_weather(self, city: str, uf: str):
        from OSDroupa.ai.weather import WeatherUnavailable, get_weather_context

        self.weather_loading = True
        try:
            context = await get_weather_context(city, uf)
            self.weather_context = {key: str(value) for key, value in context.items() if key != "manual"}
            self.weather_context["manual"] = ""
            self.daily_weather = context["categoria"]
            self.weather_notice = ""
        except WeatherUnavailable as exc:
            self.weather_notice = f"{exc} Escolha o clima manualmente para continuar."
        finally:
            self.weather_loading = False

    async def load_weather_context(self):
        """Carrega a previsão real da cidade do endereço padrão (Change 024)."""
        status = await self._session_gate()
        if status != "ok":
            return
        try:
            city, uf = await self._default_address_city()
        except (httpx.HTTPError, ValueError):
            city, uf = "", ""
        if not city:
            self.weather_notice = "Cadastre um endereço padrão ou informe uma cidade para usar a previsão real."
            return
        await self._apply_weather(city, uf)

    async def search_weather_city(self):
        query = self.weather_city_query.strip()
        city, _, uf = query.partition("/")
        if len(city.strip()) < 2:
            self.weather_notice = "Informe o nome de uma cidade."
            return
        previous = dict(self.weather_context)
        await self._apply_weather(city.strip(), uf.strip().upper()[:2])
        if self.weather_notice and previous:
            self.weather_context = previous

    def set_daily_occasion(self, value: str):
        if value in LOOK_OCCASIONS:
            self.daily_occasion = value

    async def save_daily_look(self):
        if not self.daily_suggestions:
            self.experience_error = "Monte uma combinação antes de salvar."
            return
        local_key = uuid.uuid4().hex
        try:
            response = await self._life_request("POST", "meusLooks", payload={
                "chave_local": local_key,
                "nome": f"Look {self.daily_occasion} · {self.daily_weather}",
                "ocasiao": self.daily_occasion,
                "data_planejada": datetime.now(timezone.utc).date().isoformat(),
                "roupa_chaves": [item["local_id"] for item in self.daily_suggestions],
            })
            response.raise_for_status()
            self.experience_notice = "Combinação salva em Meus Looks."
            self.experience_error = ""
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível salvar este look agora.")

    async def load_usage_history(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        if status == "retry":
            self.experience_error = self.session_error or "Não foi possível validar sua conta."
            return
        await self.load_wardrobe()
        self.experience_error = ""
        try:
            response = await self._life_request("GET", "historicoUso")
            response.raise_for_status()
            payload = response.json()
            self.history_items = self._string_rows(payload.get("itens", [])) if isinstance(payload, dict) else []
            self.wear_events = self._string_rows(payload.get("registros", [])) if isinstance(payload, dict) else []
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível carregar o histórico de uso.")

    async def record_wear(self, garment_id: str):
        if not str(garment_id).isdigit():
            self.experience_error = "Atualize o armário para sincronizar esta peça antes de registrar o uso."
            return
        try:
            response = await self._life_request("POST", "registrarUso", payload={"peca_id": int(garment_id), "ocasiao": self.wear_occasion})
            response.raise_for_status()
            self.experience_notice = "Uso registrado. Seu custo por uso foi atualizado quando há preço cadastrado."
            await self.load_usage_history()
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível registrar o uso desta peça.")

    def set_wear_occasion(self, value: str):
        self.wear_occasion = value[:80]

    async def load_fidelity(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        if status == "retry":
            self.experience_error = self.session_error or "Não foi possível validar sua conta."
            return
        try:
            response = await self._life_request("GET", "fidelidade")
            response.raise_for_status()
            data = response.json()
            self.loyalty_points = int(data.get("pontos", 0))
            self.loyalty_level = str(data.get("nivel", "Começo"))
            self.loyalty_next_level = str(data.get("proximo_nivel", "Fio"))
            self.loyalty_points_to_next = int(data.get("pontos_para_proximo_nivel", max(0, 25 - self.loyalty_points)))
            self.loyalty_tier_progress = int(data.get("progresso_nivel", 0))
            self.loyalty_completed = int(data.get("concluidos", 0))
            self.loyalty_challenge_total = int(data.get("desafios_validos", len(WARDROBE_CHALLENGES)))
            history = data.get("historico", [])
            self.loyalty_history = [
                {
                    "desafio_id": str(item.get("desafio_id", "")),
                    "titulo": str(item.get("titulo", "Desafio concluído")),
                    "pontos": str(item.get("pontos", 0)),
                    "concluido_em": str(item.get("concluido_em", "")),
                }
                for item in history if isinstance(item, dict)
            ] if isinstance(history, list) else []
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível carregar sua fidelidade.")

    async def load_travel_planner(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        if status == "retry":
            self.experience_error = self.session_error or "Não foi possível validar sua conta."
            return
        await self.load_wardrobe()
        try:
            response = await self._life_request("GET", "malas")
            response.raise_for_status()
            data = response.json()
            self.packing_plans = self._string_rows(data.get("malas", [])) if isinstance(data, dict) else []
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível carregar suas viagens.")

    def set_packing_name(self, value: str):
        self.packing_name = value

    def set_packing_destination(self, value: str):
        self.packing_destination = value

    def set_packing_start(self, value: str):
        self.packing_start = value

    def set_packing_end(self, value: str):
        self.packing_end = value

    def set_packing_occasion(self, value: str):
        self.packing_occasion = value[:80]

    def toggle_packing_item(self, garment_id: str):
        current = set(self.packing_selected_ids)
        if garment_id in current:
            current.remove(garment_id)
        else:
            current.add(garment_id)
        self.packing_selected_ids = sorted(current)

    async def save_packing_plan(self):
        if not self.packing_name.strip() or not self.packing_destination.strip():
            self.experience_error = "Dê um nome para a viagem e informe o destino."
            return
        try:
            response = await self._life_request("POST", "malas", payload={
                "nome": self.packing_name.strip(), "destino": self.packing_destination.strip(),
                "data_inicio": self.packing_start, "data_fim": self.packing_end,
                "ocasiao": self.packing_occasion,
                "pecas_ids": [int(item_id) for item_id in self.packing_selected_ids if item_id.isdigit()],
            })
            response.raise_for_status()
            self.experience_notice = "Mala salva na sua conta."
            self.experience_error = ""
            self.packing_name = ""
            self.packing_selected_ids = []
            await self.load_travel_planner()
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível salvar esta mala.")

    async def load_tryon(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        if status == "retry":
            self.experience_error = self.session_error or "Não foi possível validar sua conta."
            return
        await self.load_wardrobe()

    def toggle_tryon_item(self, garment_key: str):
        current = set(self.tryon_selected_ids)
        if garment_key in current:
            current.remove(garment_key)
        elif len(current) < 5:
            current.add(garment_key)
        self.tryon_selected_ids = sorted(current)

    async def load_testimonials(self):
        await self.restore_session()
        self.testimonials = []
        self.my_testimonials = []
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(f"{XANO_PDB}/depoimentosPublicos")
            response.raise_for_status()
            payload = response.json()
            self.testimonials = self._string_rows(payload.get("depoimentos", [])) if isinstance(payload, dict) else []
            if self.account_validated:
                response = await self._life_request("GET", "meusDepoimentos")
                response.raise_for_status()
                data = response.json()
                self.my_testimonials = self._string_rows(data.get("depoimentos", [])) if isinstance(data, dict) else []
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível carregar os relatos agora.")

    def set_testimonial_text(self, value: str):
        self.testimonial_text = value[:1500]

    def set_testimonial_anonymous(self, value: bool):
        self.testimonial_anonymous = value

    def set_testimonial_consent(self, value: bool):
        self.testimonial_consent = value

    async def submit_testimonial(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        if status != "ok":
            self.experience_error = self.session_error or "Entre para enviar sua experiência."
            return
        try:
            response = await self._life_request("POST", "depoimentos", payload={"texto": self.testimonial_text, "anonimo": self.testimonial_anonymous, "autorizo_publicacao": self.testimonial_consent})
            response.raise_for_status()
            self.experience_notice = "Relato enviado para revisão. Ele só aparece publicamente após aprovação."
            self.testimonial_text = ""
            self.testimonial_consent = False
            await self.load_testimonials()
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível enviar seu relato.")

    async def load_service_requests(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        if status == "retry":
            self.experience_error = self.session_error or "Não foi possível validar sua conta."
            return
        try:
            response = await self._life_request("GET", "solicitarAjuste")
            response.raise_for_status()
            data = response.json()
            self.tailoring_requests = self._string_rows(data.get("solicitacoes", [])) if isinstance(data, dict) else []
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível carregar suas solicitações.")

    def set_tailoring_service(self, value: str):
        self.tailoring_service = value

    def set_tailoring_garment(self, value: str):
        self.tailoring_garment = value

    def set_tailoring_notes(self, value: str):
        self.tailoring_notes = value[:2000]

    def set_tailoring_date(self, value: str):
        self.tailoring_date = value

    async def submit_tailoring_request(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        try:
            response = await self._life_request("POST", "solicitarAjuste", payload={"servico": self.tailoring_service, "peca": self.tailoring_garment, "observacoes": self.tailoring_notes, "data_preferida": self.tailoring_date})
            response.raise_for_status()
            self.experience_notice = "Solicitação registrada. A equipe ainda precisa combinar orçamento e prazo."
            self.tailoring_garment = ""
            self.tailoring_notes = ""
            await self.load_service_requests()
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível registrar o pedido de ajuste.")

    async def load_privacy_page(self):
        await self.restore_session()
        if not self.account_validated:
            return
        try:
            response = await self._life_request("GET", "solicitacoesPrivacidade")
            response.raise_for_status()
            data = response.json()
            self.privacy_requests = self._string_rows(data.get("solicitacoes", [])) if isinstance(data, dict) else []
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível carregar suas solicitações de dados.")

    def set_privacy_request_type(self, value: str):
        self.privacy_request_type = value

    def set_privacy_details(self, value: str):
        self.privacy_details = value[:2000]

    async def submit_privacy_request(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        try:
            response = await self._life_request("POST", "solicitacoesPrivacidade", payload={"tipo": self.privacy_request_type, "detalhes": self.privacy_details})
            response.raise_for_status()
            self.experience_notice = "Solicitação salva na sua conta para análise."
            self.privacy_details = ""
            await self.load_privacy_page()
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível registrar a solicitação.")

    async def load_admin_testimonials(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        try:
            response = await self._life_request("GET", "adminDepoimentos")
            response.raise_for_status()
            data = response.json()
            self.admin_testimonials = self._string_rows(data.get("depoimentos", [])) if isinstance(data, dict) else []
            self.experience_error = ""
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível carregar a fila de relatos. Acesse com papel admin.")

    async def moderate_testimonial(self, testimonial_id: str, status: str):
        if status not in {"Publicado", "Recusado"} or not str(testimonial_id).isdigit():
            return
        try:
            response = await self._life_request("PATCH", f"adminDepoimentos/{testimonial_id}", payload={"status": status})
            response.raise_for_status()
            self.experience_notice = "Relato atualizado."
            await self.load_admin_testimonials()
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "Não foi possível moderar o relato.")


    async def load_admin_privacy_requests(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        try:
            response = await self._life_request("GET", "adminSolicitacoesPrivacidade")
            response.raise_for_status()
            data = response.json()
            self.admin_privacy_requests = self._string_rows(data.get("solicitacoes", [])) if isinstance(data, dict) else []
            self.experience_error = ""
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "NÃ£o foi possÃ­vel carregar as solicitaÃ§Ãµes. Acesse com papel admin.")

    async def update_privacy_request(self, request_id: str, status: str):
        if status not in {"Em anÃ¡lise", "ConcluÃ­da", "NÃ£o aplicÃ¡vel"} or not request_id.isdigit():
            return
        try:
            response = await self._life_request("PATCH", f"adminSolicitacoesPrivacidade/{request_id}", payload={"status": status})
            response.raise_for_status()
            self.experience_notice = "SolicitaÃ§Ã£o atualizada. Responda a pessoa titular pelo canal cadastrado."
            await self.load_admin_privacy_requests()
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "NÃ£o foi possÃ­vel atualizar a solicitaÃ§Ã£o.")

    async def load_admin_tailoring_requests(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        try:
            response = await self._life_request("GET", "adminSolicitacoesAjuste")
            response.raise_for_status()
            data = response.json()
            self.admin_tailoring_requests = self._string_rows(data.get("solicitacoes", [])) if isinstance(data, dict) else []
            self.experience_error = ""
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "NÃ£o foi possÃ­vel carregar a fila. Acesse com papel admin.")

    async def update_tailoring_request(self, request_id: str, status: str):
        allowed = {"Recebido", "Em anÃ¡lise", "OrÃ§amento enviado", "Agendado", "ConcluÃ­do", "Cancelado"}
        if status not in allowed or not request_id.isdigit():
            return
        try:
            response = await self._life_request("PATCH", f"adminSolicitacoesAjuste/{request_id}", payload={"status": status})
            response.raise_for_status()
            self.experience_notice = "SolicitaÃ§Ã£o da alfaiataria atualizada. Avise o cliente pelo e-mail cadastrado."
            await self.load_admin_tailoring_requests()
        except (httpx.HTTPError, ValueError) as exc:
            self.experience_error = _xano_failure_message(exc, "NÃ£o foi possÃ­vel atualizar esta solicitaÃ§Ã£o.")


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
    pairing_is_demo: bool = False
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
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.pairing_code = ""
            self.pairing_expires_at = ""
            self.pairing_error = self.session_error or "Não foi possível validar sua conta."
            return
        self.pairing_identifier = ""
        self.pairing_error = ""
        self.pairing_code = ""
        self.pairing_expires_at = ""
        self.pairing_is_demo = False

    async def load_devices(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.devices = []
            self.device_error = self.session_error or "Não foi possível validar sua conta."
            return
        self.device_loading = True
        self.device_error = ""
        self.device_notice = ""
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meusDispositivos",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                )
            if response.status_code == 401:
                self._clear_auth_tokens()
                self.account_validated = False
                return rx.redirect("/login")
            if response.status_code == 404:
                self.devices = []
                self.device_notice = "Integração com dispositivos ainda não publicada; nenhum sensor está conectado."
                return
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("dispositivos", []) if isinstance(payload, dict) else payload
            if isinstance(payload, dict) and payload.get("demonstracao"):
                self.device_notice = "Modo local de demonstração: os dados ficam neste computador e não representam sensores físicos."
            if not isinstance(rows, list):
                raise ValueError("Formato inesperado de dispositivos.")
            self.devices = [{
                "id": str(item.get("id", "")),
                "name": str(item.get("nome") or item.get("name") or "Armário inteligente"),
                "type": str(item.get("tipo") or item.get("type") or "Dispositivo"),
                "status": self._normalize_device_status(item.get("status")),
                "last_seen": str(item.get("ultimo_contato") or item.get("last_seen") or "Ainda sem leituras"),
            } for item in rows if isinstance(item, dict) and item.get("id") is not None]
            if not self.devices and not self.device_notice:
                self.device_notice = "Nenhum dispositivo conectado a esta conta."
        except (httpx.HTTPError, ValueError) as exc:
            self.device_error = _xano_failure_message(exc, "Não foi possível consultar os dispositivos. Tente novamente.")
        finally:
            self.device_loading = False

    async def request_pairing(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.pairing_code = ""
            self.pairing_expires_at = ""
            self.pairing_error = self.session_error or "Não foi possível validar sua conta."
            return
        identifier = self.pairing_identifier.strip()
        if not identifier:
            self.pairing_error = "Informe o código impresso no dispositivo."
            return
        self.pairing_loading = True
        self.pairing_error = ""
        self.pairing_code = ""
        self.pairing_is_demo = False
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(
                    f"{XANO_PDB}/solicitarPareamento",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    json={"identificador": identifier},
                )
            if response.status_code == 401:
                self._clear_auth_tokens()
                self.account_validated = False
                return rx.redirect("/login")
            if response.status_code == 404:
                self.pairing_error = "O serviço de pareamento ainda não está publicado no Xano. Nenhum dispositivo foi conectado."
                return
            response.raise_for_status()
            payload = response.json()
            self.pairing_code = str(payload.get("codigo_pareamento") or "")
            self.pairing_expires_at = str(payload.get("expira_em") or "")
            self.pairing_is_demo = bool(payload.get("demonstracao"))
            if not self.pairing_code:
                raise ValueError("Código de pareamento ausente.")
        except (httpx.HTTPError, ValueError) as exc:
            self.pairing_error = _xano_failure_message(exc, "Não foi possível iniciar o pareamento. Verifique o código e tente novamente.")
        finally:
            self.pairing_loading = False

    async def confirm_local_pairing(self):
        if not self.pairing_is_demo or not self.pairing_code:
            return
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(
                    f"{XANO_PDB}/confirmarPareamentoLocal",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    json={"codigo_pareamento": self.pairing_code},
                )
            response.raise_for_status()
            self.pairing_error = ""
            self.pairing_code = ""
            self.pairing_is_demo = False
            return rx.redirect("/dispositivos")
        except (httpx.HTTPError, ValueError) as exc:
            self.pairing_error = _xano_failure_message(exc, "Não foi possível confirmar a demonstração.")

    async def load_device_detail(self):
        session_status = await self._session_gate()
        if session_status == "login":
            return rx.redirect("/login")
        if session_status == "retry":
            self.selected_device = {}
            self.device_events = []
            self.device_error = self.session_error or "Não foi possível validar sua conta."
            return
        device_id = str(self.router.url.query_parameters.get("id", ""))
        self.selected_device = {}
        self.device_events = []
        self.device_error = ""
        if not device_id.isdigit():
            self.device_error = "Dispositivo não encontrado."
            return
        self.device_loading = True
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_PDB}/meuDispositivo/{device_id}",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                )
            if response.status_code == 401:
                self._clear_auth_tokens()
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
        except (httpx.HTTPError, ValueError) as exc:
            self.device_error = _xano_failure_message(exc, "Não foi possível carregar os dados do dispositivo.")
        finally:
            self.device_loading = False


class ManagementState(AuthState):
    """Read-only management views; Xano enforces the admin role."""

    management_loading: bool = False
    management_error: str = ""
    management_access_denied: bool = False
    management_rows: list[dict[str, str]] = []
    product_name: str = ""
    product_description: str = ""
    product_category: str = "Roupas"
    product_brand: str = ""
    product_collection: str = ""
    product_type: str = ""
    product_sizes: str = ""
    product_colors: str = ""
    product_material: str = ""
    product_fit: str = ""
    product_price: str = ""
    product_stock: str = ""
    product_image_url: str = ""
    product_demonstration: str = "true"
    product_action_message: str = ""
    product_action_error: bool = False
    product_action_loading: bool = False
    order_action_message: str = ""
    management_page: int = 1
    management_has_next: bool = False
    management_endpoint: str = ""
    management_section: str = "list"
    management_metrics: list[dict[str, str]] = [
        {"label": "Pedidos cadastrados", "value": "—"},
        {"label": "Vendas no mês", "value": "Aguardando integração"},
        {"label": "Produtos cadastrados", "value": "—"},
        {"label": "Clientes cadastrados", "value": "—"},
    ]

    async def _load_admin_resource(self, endpoint: str, section: str):
        session_status = await self._session_gate()
        if session_status == "login":
            self.management_rows = []
            self.management_error = "Sua sessão expirou. Entre novamente."
            return rx.redirect("/login")
        if session_status == "retry":
            self.management_rows = []
            self.management_error = self.session_error or "Não foi possível validar sua conta."
            self.management_loading = False
            return
        if endpoint != self.management_endpoint:
            self.management_page = 1
        self.management_loading = True
        self.management_error = ""
        self.management_access_denied = False
        self.management_rows = []
        self.management_endpoint = endpoint
        self.management_section = section
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.get(
                    f"{XANO_DB}/{endpoint}",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    params={"page": self.management_page, "per_page": 20} if section != "dashboard" else None,
                )
            if response.status_code in (401, 403):
                self.management_access_denied = response.status_code == 403
                self.management_error = "Esta área exige uma conta administradora." if self.management_access_denied else "Sua sessão expirou. Entre novamente."
                if response.status_code == 401:
                    self._clear_auth_tokens()
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
                    ("Pedidos cadastrados", "pedidos_cadastrados"),
                    ("Vendas no mês", "vendas_mes"),
                    ("Produtos cadastrados", "produtos_cadastrados"),
                    ("Clientes cadastrados", "clientes_cadastrados"),
                ]
                self.management_metrics = [
                    {"label": label, "value": str(data.get(key, "—"))}
                    for label, key in aliases
                ]
            else:
                self.management_has_next = False
                if isinstance(payload, dict):
                    rows = next((payload.get(key) for key in ("itens", "items", "pedidos", "produtos", "clientes", "relatorios") if isinstance(payload.get(key), list)), [])
                    if "nextPage" in payload:
                        self.management_has_next = payload.get("nextPage") is not None
                    elif "next_page" in payload:
                        self.management_has_next = payload.get("next_page") is not None
                    else:
                        self.management_has_next = len(rows) == 20
                else:
                    rows = payload
                    self.management_has_next = isinstance(rows, list) and len(rows) == 20
                if not isinstance(rows, list):
                    raise ValueError("Formato inesperado na resposta de gestão.")
                normalized_rows = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    record_id = str(row.get("id", ""))
                    raw_status = row.get("status")
                    if isinstance(raw_status, dict):
                        status = raw_status.get("Status") or raw_status.get("status") or raw_status.get("status_cliente") or "—"
                    else:
                        status = raw_status or row.get("status_pedido_id") or row.get("status_cliente_id") or "—"
                    if section == "products":
                        status = row.get("Categoria") or "Sem categoria"
                        detail = f"{row.get('Qtd_Disp') or 0} un. · R$ {row.get('Preco') or '—'}"
                    elif section == "orders":
                        detail = f"R$ {row.get('Total') or '—'} · {row.get('created_at') or ''}"
                    elif section == "customers":
                        detail = row.get("celular") or row.get("created_at") or ""
                    else:
                        detail = f"R$ {row.get('Total') or '—'} · {row.get('created_at') or ''}"
                    normalized_rows.append({
                        "id": record_id,
                        "name": str(row.get("Nome") or row.get("nome") or row.get("name") or row.get("email") or (f"Pedido #{record_id}" if section == "orders" else f"Registro {record_id}")),
                        "status": str(status),
                        "detail": str(detail),
                    })
                self.management_rows = normalized_rows
        except (httpx.HTTPError, ValueError) as exc:
            self.management_error = _xano_failure_message(exc, "Não foi possível carregar os dados da gestão. Tente novamente.")
        finally:
            self.management_loading = False

    async def next_management_page(self):
        if self.management_has_next and not self.management_loading and self.management_endpoint:
            self.management_page += 1
            return await self._load_admin_resource(self.management_endpoint, self.management_section)

    async def previous_management_page(self):
        if self.management_page > 1 and not self.management_loading and self.management_endpoint:
            self.management_page -= 1
            return await self._load_admin_resource(self.management_endpoint, self.management_section)

    async def retry_management(self):
        if self.management_endpoint:
            return await self._load_admin_resource(self.management_endpoint, self.management_section)

    async def load_dashboard(self):
        return await self._load_admin_resource("adminResumo", "dashboard")

    async def load_products(self):
        return await self._load_admin_resource("adminProdutos", "products")

    async def load_orders(self):
        return await self._load_admin_resource("adminPedidos", "orders")

    async def load_customers(self):
        return await self._load_admin_resource("adminClientes", "customers")

    async def load_reports(self):
        return await self._load_admin_resource("adminRelatorios", "reports")

    def set_product_name(self, value: str):
        self.product_name = value
        self.product_action_message = ""

    def set_product_description(self, value: str):
        self.product_description = value

    def set_product_category(self, value: str):
        self.product_category = value

    def set_product_brand(self, value: str):
        self.product_brand = value

    def set_product_collection(self, value: str):
        self.product_collection = value

    def set_product_type(self, value: str):
        self.product_type = value

    def set_product_sizes(self, value: str):
        self.product_sizes = value

    def set_product_colors(self, value: str):
        self.product_colors = value

    def set_product_material(self, value: str):
        self.product_material = value

    def set_product_fit(self, value: str):
        self.product_fit = value

    def set_product_price(self, value: str):
        self.product_price = value
        self.product_action_message = ""

    def set_product_stock(self, value: str):
        self.product_stock = value
        self.product_action_message = ""

    def set_product_image_url(self, value: str):
        self.product_image_url = value

    def set_product_demonstration(self, value: str):
        self.product_demonstration = "false" if value == "Venda real · Mercado Pago" else "true"

    @rx.var
    def product_sale_mode(self) -> str:
        return "Demonstração sem cobrança" if self.product_demonstration == "true" else "Venda real · Mercado Pago"

    async def create_product(self):
        if not self.product_name.strip() or not self.product_price.strip() or not self.product_stock.strip():
            self.product_action_error = True
            self.product_action_message = "Preencha nome, preço e estoque."
            return
        self.product_action_loading = True
        self.product_action_message = ""
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.post(
                    f"{XANO_DB}/adminProdutos",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    json={
                        "Nome": self.product_name.strip(),
                        "Descricao": self.product_description.strip(),
                        "Categoria": self.product_category,
                        "Marca": self.product_brand.strip() or "OSDROUPA",
                        "Colecao": self.product_collection.strip() or "Coleção da loja",
                        "Tipo": self.product_type.strip() or self.product_category,
                        "Tamanhos": self.product_sizes.strip() or "Consultar disponibilidade",
                        "Cores": self.product_colors.strip() or "Consultar disponibilidade",
                        "Material": self.product_material.strip() or "Material a confirmar",
                        "Caimento": self.product_fit.strip() or "Consultar tabela de medidas",
                        "Preco": self.product_price,
                        "Qtd_Disp": self.product_stock,
                        "Url_Imagem": self.product_image_url.strip(),
                        "demonstracao": self.product_demonstration == "true",
                    },
                )
            if response.status_code == 401:
                self._clear_auth_tokens()
                self.account_validated = False
                return rx.redirect("/login")
            response.raise_for_status()
            self.product_action_error = False
            self.product_action_message = "Produto cadastrado no catálogo."
            self.product_name = ""
            self.product_description = ""
            self.product_brand = ""
            self.product_collection = ""
            self.product_type = ""
            self.product_sizes = ""
            self.product_colors = ""
            self.product_material = ""
            self.product_fit = ""
            self.product_price = ""
            self.product_stock = ""
            self.product_image_url = ""
            self.product_demonstration = "true"
            global _public_catalog_cache, _public_catalog_cache_at
            _public_catalog_cache = None
            _public_catalog_cache_at = 0.0
            await self._load_admin_resource("adminProdutos", "products")
        except (httpx.HTTPError, ValueError) as exc:
            self.product_action_error = True
            self.product_action_message = _xano_failure_message(exc, "Não foi possível cadastrar o produto.")
        finally:
            self.product_action_loading = False

    async def change_order_status(self, order_id: str, status: str):
        self.order_action_message = ""
        try:
            async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
                response = await client.patch(
                    f"{XANO_DB}/adminPedidoStatus",
                    headers={"Authorization": f"Bearer {self._current_auth_token()}"},
                    json={"pedido_id": order_id, "status": status},
                )
            if response.status_code in (401, 403):
                self.management_access_denied = response.status_code == 403
                self.management_error = "Esta ação exige uma conta administradora." if response.status_code == 403 else "Sua sessão expirou. Entre novamente."
                return rx.redirect("/login") if response.status_code == 401 else None
            response.raise_for_status()
            self.order_action_message = f"Pedido atualizado para {status}."
            await self._load_admin_resource("adminPedidos", "orders")
        except (httpx.HTTPError, ValueError) as exc:
            self.order_action_message = _xano_failure_message(exc, "Não foi possível atualizar o pedido.")


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

def password_field(
    label: str,
    placeholder: str,
    value,
    on_change,
    toggle: bool = False,
    preserve_typed_value: bool = False,
) -> rx.Component:
    input_type = rx.cond(AuthState.show_password, "text", "password")

    # Keep login keystrokes in the browser while Reflex syncs each change to
    # server state; a server render should not replace a value being edited.
    value_props = {"default_value": value} if preserve_typed_value else {"value": value}
    input_element = rx.input(
        placeholder=placeholder,
        on_change=on_change,
        type=input_type,
        size="3",
        **value_props,
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
        field("E-mail", placeholder="seu.email@exemplo.com", default_value=AuthState.login_email, on_change=AuthState.set_login_email, type="email"),
        password_field(
            "Senha",
            "Digite sua senha",
            AuthState.login_password,
            AuthState.set_login_password,
            toggle=True,
            preserve_typed_value=True,
        ),
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
                rx.text(
                    AuthState.forgot_password_msg,
                    font_size="0.82rem",
                    color=rx.cond(AuthState.forgot_password_error, ERROR, MUTED),
                    line_height="1.5",
                ),
                padding="8px 12px",
                border_radius="8px",
                background=MUTED_BG,
                width="100%",
            ),
        ),
        rx.cond(
            AuthState.forgot_password_link != "",
            rx.link(
                "Abrir link local de redefinição",
                href=AuthState.forgot_password_link,
                color=DENIM,
                font_weight="700",
                font_size="0.86rem",
                text_decoration="underline",
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
def site_navbar() -> rx.Component:
    """Cabe\u00e7alho \u00fanico para a loja, o conte\u00fado e o espa\u00e7o da conta."""
    primary = [
        ("Loja", "/loja", "shopping-bag"),
        ("Inspira\u00e7\u00e3o", "/inspiracao", "sparkles"),
        ("Servi\u00e7os", "/servicos", "scissors"),
        ("Novidades", "/novidades", "zap"),
    ]
    secondary = [
        ("Como funciona", "/como-funciona"),
        ("Depoimentos", "/depoimentos"),
        ("Caderno", "/artigos"),
        ("Desafios", "/desafios"),
        ("Privacidade", "/privacidade"),
    ]
    personal = [
        ("Arm\u00e1rio", "/armario", "shirt"),
        ("Looks", "/looks", "sparkles"),
        ("Look do dia", "/look-do-dia", "sun"),
        ("Fidelidade", "/fidelidade", "award"),
        ("Agenda", "/calendario", "calendar-days"),
        ("Pedidos", "/pedidos", "package-check"),
        ("Perfil", "/perfil", "user-round"),
        ("Dispositivos", "/dispositivos", "radio"),
        ("Endere\u00e7os", "/enderecos", "map-pin"),
    ]

    brand = rx.link(
        rx.hstack(
            rx.box(rx.html(LOGO_SVG), class_name="osd-brand-mark"),
            rx.vstack(
                rx.text("OSDROUPA", font_family=DISPLAY, font_weight="800", font_size=["1.02rem", "1.12rem"], color=CHALK, letter_spacing="0.055em"),
                rx.text("LOJA \u00b7 ALFAIATARIA \u00b7 ARM\u00c1RIO INTELIGENTE", font_size="0.55rem", font_weight="700", color=THREAD, letter_spacing="0.105em", display=["none", "block"], class_name="osd-brand-caption"),
                spacing="0",
                align_items="flex-start",
            ),
            spacing="2",
            align_items="center",
            flex_shrink="0",
        ),
        href="/",
        aria_label="OSDROUPA \u2014 p\u00e1gina inicial",
        _hover={"opacity": "0.9"},
    )

    primary_links = [
        rx.link(
            rx.hstack(rx.icon(icon, size=15), rx.text(label), spacing="2", align="center"),
            href=href,
            class_name="osd-nav-primary",
        )
        for label, href, icon in primary
    ]
    public_secondary = [
        rx.link(label, href=href, class_name="osd-nav-secondary")
        for label, href in secondary
    ]
    personal_desktop = [
        rx.link(label, href=href, class_name="osd-nav-secondary")
        for label, href, _icon in personal
    ]
    mobile_public = [
        rx.link(
            label,
            href=href,
            class_name="osd-nav-pill",
            font_size="0.8rem",
            font_weight="600",
        )
        for label, href, _icon in primary
    ] + [
        rx.link(
            label,
            href=href,
            class_name="osd-nav-pill",
            font_size="0.8rem",
            font_weight="600",
        )
        for label, href in secondary
    ]
    mobile_personal = rx.cond(
        AuthState.account_validated,
        rx.hstack(
            *[
                rx.link(
                    label,
                    href=href,
                    class_name="osd-nav-pill",
                    font_size="0.8rem",
                    font_weight="600",
                )
                for label, href, _icon in personal
            ],
            rx.button(
                rx.hstack(rx.icon("log-out", size=14), rx.text("Sair"), spacing="2"),
                on_click=AuthState.logout,
                class_name="osd-nav-pill",
                cursor="pointer",
            ),
            spacing="2",
            width="max-content",
        ),
        rx.hstack(
            rx.link("Entrar", href="/login", class_name="osd-nav-pill", font_size="0.8rem", font_weight="600"),
            rx.link("Criar conta", href="/cadastro", class_name="osd-nav-pill", font_size="0.8rem", font_weight="700", color=INK, background=THREAD),
            spacing="2",
            width="max-content",
        ),
    )

    cart_link = rx.link(
        rx.hstack(
            rx.icon("shopping-bag", size=16, color=THREAD),
            rx.text("Sacola", color=CHALK, font_weight="700", font_size="0.82rem", class_name="osd-cart-label"),
            rx.badge(StoreState.cart_count, color_scheme="amber", variant="solid", border_radius="999px"),
            spacing="2",
            align="center",
        ),
        href="/carrinho",
        padding="0.55rem 0.8rem",
        border="1px solid rgba(233,162,59,.3)",
        border_radius="999px",
        background="rgba(233,162,59,.09)",
        flex_shrink="0",
        _hover={"background": "rgba(233,162,59,.16)", "transform": "translateY(-1px)"},
    )
    account_action = rx.cond(
        AuthState.account_validated,
        rx.link(
            rx.hstack(rx.icon("user-round", size=15), rx.text("Minha conta"), spacing="2"),
            href="/perfil",
            color=CHALK,
            font_size="0.82rem",
            font_weight="700",
            white_space="nowrap",
            padding="0.58rem 0.86rem",
            border="1px solid rgba(255,255,255,.14)",
            border_radius="999px",
            _hover={"background": "rgba(255,255,255,.08)", "color": THREAD},
        ),
        rx.link(
            rx.hstack(rx.text("Entrar"), rx.icon("arrow-up-right", size=14, class_name="osd-account-arrow"), spacing="2"),
            href="/login",
            color=INK,
            font_size="0.82rem",
            font_weight="800",
            white_space="nowrap",
            padding="0.58rem 0.9rem",
            background=THREAD,
            border_radius="999px",
            _hover={"transform": "translateY(-1px)", "box_shadow": "0 8px 22px rgba(233,162,59,.24)"},
        ),
    )

    return rx.box(
        rx.vstack(
            rx.hstack(
                brand,
                rx.spacer(),
                rx.hstack(*primary_links, spacing="4", align="center", display=["none", "none", "none", "none", "flex"]),
                rx.spacer(),
                cart_link,
                account_action,
                width="100%",
                align="center",
                spacing="3",
                class_name="osd-header-primary",
            ),
            rx.hstack(
                rx.hstack(*public_secondary, spacing="4", align="center", flex_wrap="wrap"),
                rx.spacer(),
                rx.cond(
                    AuthState.account_validated,
                    rx.hstack(
                        *personal_desktop,
                        rx.button("Sair", on_click=AuthState.logout, variant="ghost", color="rgba(248,249,250,.7)", font_size="0.76rem", font_weight="600", padding_x="0.3rem"),
                        spacing="4",
                        align="center",
                        flex_wrap="wrap",
                    ),
                    rx.hstack(rx.icon("sparkles", size=14, color=THREAD), rx.text("Seu estilo, no seu ritmo.", color="rgba(248,249,250,.58)", font_size="0.74rem"), spacing="2", align="center"),
                ),
                class_name="osd-header-secondary",
                width="100%",
                align="center",
                spacing="4",
                display=["none", "none", "none", "none", "flex"],
            ),
            rx.box(
                rx.hstack(
                    *mobile_public,
                    mobile_personal,
                    spacing="2",
                    width="max-content",
                    min_width="100%",
                    align="center",
                ),
                class_name="osd-mobile-nav",
                overflow_x="auto",
                overflow_y="hidden",
                width="100%",
                padding_y="0.35rem",
                display=["block", "block", "block", "block", "none"],
                aria_label="Navega\u00e7\u00e3o do OSDROUPA",
            ),
            spacing="0",
            width="100%",
            max_width="1320px",
            margin_x="auto",
        ),
        class_name="osd-site-header",
        padding_x=["1rem", "1.4rem", "2rem"],
        width="100%",
    )


def home_navbar() -> rx.Component:
    """Compatibilidade com as p?ginas institucionais; usa a navega??o compartilhada."""
    return site_navbar()

def marketing_scroll_progress() -> rx.Component:
    return rx.box(class_name="osd-scroll-progress", aria_hidden="true")


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
                "Organize suas peças, experimente combinações e planeje seus looks em um espaço feito para acompanhar o seu estilo.",
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
                            rx.text("Criar minha conta"),
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
                            rx.text("Como funciona"),
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
                    href="/como-funciona",
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


def home_scroll_cue() -> rx.Component:
    return rx.link(
        rx.vstack(
            rx.text("Desça para descobrir", color="rgba(248,249,250,0.64)", font_size="0.72rem", font_weight="700", letter_spacing="0.1em"),
            rx.icon("chevron-down", size=20, color=THREAD),
            spacing="1",
            align="center",
        ),
        href="#recursos",
        class_name="osd-scroll-cue",
        display="flex",
        justify_content="center",
        width="100%",
        padding_bottom="1rem",
        aria_label="Descer para descobrir os recursos do OSDROUPA",
    )


def home_marquee_strip() -> rx.Component:
    """Faixa animada com os fluxos que a plataforma oferece."""
    items = [
        "🧵 Armário digital",
        "🎨 Combinações do seu jeito",
        "🗓️ Planejamento de looks",
        "🧵 Alfaiataria sob demanda",
        "🛍️ Loja de moda",
        "🌱 Reuso com mais intenção",
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
            "tag": "SEU ACERVO",
            "title": "Armário em um só lugar",
            "desc": "Cadastre suas peças por categoria e mantenha seu acervo organizado para encontrar cada item com facilidade.",
            "color": THREAD,
        },
        {
            "icon": "radio",
            "tag": "COMBINAÇÕES",
            "title": "Looks do seu jeito",
            "desc": "Crie combinações com as peças que você já tem e salve suas ideias para consultar depois.",
            "color": THREAD,
        },
        {
            "icon": "map-pin",
            "tag": "PLANEJAMENTO",
            "title": "Agenda de combinações",
            "desc": "Planeje seus looks para os próximos dias e deixe suas escolhas organizadas no calendário pessoal.",
            "color": THREAD,
        },
        {
            "icon": "scissors",
            "tag": "ALFAIATARIA",
            "title": "Ajustes que fazem sentido",
            "desc": "Conheça caminhos para ajustar, reparar ou transformar peças e dar mais vida ao que já faz parte do seu estilo.",
            "color": THREAD,
        },
        {
            "icon": "leaf",
            "tag": "ESCOLHAS CONSCIENTES",
            "title": "Mais vida para suas peças",
            "desc": "Redescubra o que já está no seu armário e explore novas formas de combinar, cuidar e usar cada peça.",
            "color": THREAD,
        },
        {
            "icon": "shield-check",
            "tag": "SUA CONTA",
            "title": "Seu espaço pessoal",
            "desc": "Acesse seus dados de perfil, endereços, peças e combinações dentro de uma conta só sua.",
            "color": THREAD,
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
                "box_shadow": "0 16px 40px rgba(0,0,0,0.4)",
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
        class_name="osd-story-reveal",
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
        id="manifesto",
        class_name="osd-story-reveal",
        padding_y=["2rem", "4rem"],
        padding_x=["1.2rem", "2rem"],
        width="100%",
    )


def home_how_section() -> rx.Component:
    steps = [
        ("01", "Cadastre suas peças", "Monte seu acervo digital no seu ritmo, organizando o que você já tem."),
        ("02", "Crie combinações", "Experimente diferentes peças, salve seus looks e planeje quando usar cada um."),
        ("03", "Vista com intenção", "Volte às suas ideias, descubra novas possibilidades e cuide melhor do seu guarda-roupa."),
    ]
    cards = [
        rx.box(
            rx.vstack(
                rx.text(number, font_family=DISPLAY, font_size="2.1rem", font_weight="800", color=THREAD),
                rx.heading(title, font_family=DISPLAY, font_size="1.2rem", color=CHALK),
                rx.text(description, font_size="0.9rem", line_height="1.6", color="rgba(248,249,250,0.7)"),
                spacing="2", align_items="flex-start", width="100%",
            ),
            padding=["1.25rem", "1.6rem"],
            background="rgba(255,255,255,0.04)",
            border="1px solid rgba(255,255,255,0.1)",
            border_radius="22px",
            width="100%",
        )
        for number, title, description in steps
    ]
    return rx.box(
        rx.vstack(
            rx.text("SIMPLES DE COMEÇAR", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.14em"),
            rx.heading("Seu estilo, em três passos.", font_family=DISPLAY, font_size=["2rem", "2.7rem"], color=CHALK, letter_spacing="-0.03em", text_align="center"),
            rx.text("Um espaço pessoal para organizar, combinar e planejar suas roupas.", color="rgba(248,249,250,0.72)", text_align="center", max_width="600px", line_height="1.6"),
            rx.grid(*cards, columns={"initial": "1", "md": "3"}, spacing="4", width="100%"),
            rx.link("Ver o passo a passo completo →", href="/como-funciona", color=THREAD, font_weight="700", padding_top="0.4rem"),
            spacing="4", align_items="center", width="100%", max_width="1220px", margin_x="auto",
        ),
        id="como-funciona",
        class_name="osd-story-reveal",
        padding_y=["3.5rem", "5rem"],
        padding_x=["1.1rem", "2rem"],
        background="rgba(10,17,34,0.38)",
        width="100%",
    )


def home_services_teaser() -> rx.Component:
    return rx.box(
        rx.grid(
            rx.vstack(
                rx.text("ALFAIATARIA & CUIDADO", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.14em"),
                rx.heading("A roupa certa merece um caimento que acompanha você.", font_family=DISPLAY, font_size=["2rem", "2.7rem"], color=INK, line_height="1.08", letter_spacing="-0.03em"),
                rx.text("Ajustes, reparos e transformações para manter por perto as peças que contam a sua história.", color=MUTED, line_height="1.7", max_width="570px"),
                rx.link(
                    rx.hstack(rx.text("Conhecer serviços"), rx.icon("arrow-right", size=17), spacing="2", align="center"),
                    href="/servicos",
                    color=CHALK,
                    background=INK,
                    padding="0.85rem 1.2rem",
                    border_radius="999px",
                    font_weight="700",
                ),
                spacing="4", align_items="flex-start", width="100%",
            ),
            rx.box(
                rx.vstack(
                    rx.center(rx.icon("scissors", size=36, color=THREAD), width="76px", height="76px", border_radius="24px", background="rgba(233,162,59,0.13)"),
                    rx.heading("Feito para durar", font_family=DISPLAY, font_size="1.5rem", color=CHALK),
                    rx.text("Menos pressa para descartar. Mais cuidado com o que tem a sua medida.", color="rgba(248,249,250,0.72)", text_align="center", line_height="1.6", max_width="330px"),
                    spacing="3", align="center", width="100%",
                ),
                padding=["1.6rem", "2.4rem"],
                background=f"linear-gradient(145deg, {INK}, {DENIM})",
                border="1px solid rgba(233,162,59,0.22)",
                border_radius="28px",
                min_height="280px",
                justify_content="center",
            ),
            columns={"initial": "1", "lg": "1.15fr 0.85fr"},
            spacing="6",
            align_items="center",
            width="100%",
            max_width="1160px",
            margin_x="auto",
        ),
        class_name="osd-story-reveal",
        padding_y=["3.5rem", "5.5rem"],
        padding_x=["1.1rem", "2rem"],
        background="#F7F5EF",
        width="100%",
    )


def home_testimonials_teaser() -> rx.Component:
    stories = [
        ("01", "Praticidade", "Um lugar para deixar as escolhas do dia mais simples."),
        ("02", "Expressão", "Combinações que respeitam o seu jeito de vestir."),
        ("03", "Cuidado", "Mais atenção às peças que já fazem parte da sua história."),
    ]
    cards = [
        rx.box(
            rx.vstack(
                rx.text(number, color=THREAD, font_family=DISPLAY, font_weight="800", font_size="1.5rem"),
                rx.heading(title, color=CHALK, font_family=DISPLAY, font_size="1.1rem"),
                rx.text(description, color="rgba(248,249,250,0.66)", font_size="0.88rem", line_height="1.6"),
                spacing="2", align_items="flex-start",
            ),
            padding="1.25rem",
            background="rgba(255,255,255,0.035)",
            border="1px solid rgba(255,255,255,0.09)",
            border_radius="18px",
        )
        for number, title, description in stories
    ]
    return rx.box(
        rx.vstack(
            rx.text("A COMUNIDADE COMEÇA COM VOCÊ", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.14em"),
            rx.heading("Cada armário tem uma história.", font_family=DISPLAY, color=CHALK, font_size=["2rem", "2.7rem"], text_align="center", letter_spacing="-0.03em"),
            rx.text("Estamos abrindo este espaço para experiências reais. Quando a comunidade compartilhar suas histórias, elas aparecerão aqui com transparência.", color="rgba(248,249,250,0.7)", max_width="720px", text_align="center", line_height="1.65"),
            rx.grid(*cards, columns={"initial": "1", "sm": "2", "lg": "3"}, spacing="4", width="100%"),
            rx.link("Conhecer a comunidade →", href="/depoimentos", color=THREAD, font_weight="700"),
            spacing="4", align_items="center", width="100%", max_width="1120px", margin_x="auto",
        ),
        id="depoimentos",
        class_name="osd-story-reveal",
        padding_y=["3.5rem", "5.5rem"],
        padding_x=["1.1rem", "2rem"],
        background="#0A1122",
        width="100%",
    )


def home_numbers_banner() -> rx.Component:
    """Resumo visual das possibilidades do produto, sem estatísticas simuladas."""
    stats = [
        {"num": "03", "label": "passos para começar", "sub": "Cadastre, combine e planeje"},
        {"num": "01", "label": "armário digital", "sub": "Seu acervo em um só espaço"},
        {"num": "∞", "label": "novas combinações", "sub": "Criatividade com o que você tem"},
        {"num": "Seu", "label": "ritmo, suas escolhas", "sub": "Um espaço pessoal para o seu estilo"},
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
        id="possibilidades",
        class_name="osd-story-reveal",
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
                    "Comece pelo que você já tem: organize suas peças, crie combinações e planeje seu próximo look.",
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
        id="comece-agora",
        class_name="osd-story-reveal",
        padding_y=["3rem", "5rem"],
        padding_x=["1.2rem", "2rem"],
        width="100%",
    )


def marketing_page_shell(*sections: rx.Component) -> rx.Component:
    return rx.box(
        rx.el.style(CSS),
        home_navbar(),
        marketing_scroll_progress(),
        *sections,
        home_footer(),
        min_height="100vh",
        width="100%",
        background="#F7F5EF",
        font_family=BODY,
    )


def services_page() -> rx.Component:
    services = [
        ("scissors", "Ajuste de caimento", "Pequenas correções para aproximar a roupa do corpo e do conforto que você procura."),
        ("ruler", "Bainhas e reparos", "Cuidados do dia a dia para manter suas peças em uso por mais tempo."),
        ("sparkles", "Transformação criativa", "Novas possibilidades para uma peça que pede mudança de forma, detalhe ou acabamento."),
        ("shirt", "Curadoria do armário", "Organize seu acervo e identifique quais peças merecem um ajuste ou um novo jeito de usar."),
    ]
    service_cards = [
        rx.box(
            rx.vstack(
                rx.center(rx.icon(icon_name, size=22, color=THREAD), width="52px", height="52px", border_radius="16px", background="rgba(233,162,59,0.14)"),
                rx.heading(title, font_family=DISPLAY, font_size="1.15rem", color=INK),
                rx.text(description, color=MUTED, font_size="0.9rem", line_height="1.65"),
                spacing="3", align_items="flex-start", width="100%",
            ),
            background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding=["1.25rem", "1.5rem"], width="100%",
            box_shadow="0 12px 32px rgba(15,26,51,0.045)",
        )
        for icon_name, title, description in services
    ]
    process_steps = [
        ("01", "Escolha a peça", "Separe o que você gostaria de ajustar, reparar ou transformar."),
        ("02", "Observe o caimento", "Anote o que incomoda, o que funciona e como você quer se sentir ao vestir."),
        ("03", "Defina o próximo passo", "Compare os tipos de cuidado e escolha uma solução compatível com a peça."),
    ]
    process_cards = [
        rx.vstack(
            rx.text(number, color=THREAD, font_family=DISPLAY, font_size="1.8rem", font_weight="800"),
            rx.heading(title, color=CHALK, font_family=DISPLAY, font_size="1.15rem"),
            rx.text(description, color="rgba(248,249,250,0.68)", font_size="0.88rem", line_height="1.6"),
            spacing="2", align_items="flex-start", background="rgba(255,255,255,0.045)", border="1px solid rgba(255,255,255,0.1)", border_radius="18px", padding="1.2rem", width="100%",
        )
        for number, title, description in process_steps
    ]
    hero_visual = rx.box(
        rx.vstack(
            rx.hstack(rx.icon("scissors", size=19, color=THREAD), rx.text("CUIDADO COM A PEÇA", color=THREAD, font_size="0.68rem", font_weight="800", letter_spacing="0.13em"), spacing="2", align="center"),
            rx.heading("O detalhe muda tudo.", color=CHALK, font_family=DISPLAY, font_size=["1.55rem", "2rem"], line_height="1.1"),
            rx.text("Ajustar também é uma forma de redescobrir o que você já ama vestir.", color="rgba(248,249,250,0.73)", line_height="1.65"),
            rx.hstack(rx.icon("move-right", size=17, color=THREAD), rx.text("Caimento", color=CHALK, font_size="0.84rem"), rx.spacer(), rx.icon("heart", size=17, color=THREAD), rx.text("Cuidado", color=CHALK, font_size="0.84rem"), width="100%", align="center", padding_top="0.5rem"),
            spacing="4", align_items="flex-start", width="100%",
        ),
        padding=["1.5rem", "2.1rem"],
        background="linear-gradient(145deg, #1F3560, #0F1A33 72%)",
        border="1px solid rgba(233,162,59,0.25)",
        border_radius="28px",
        box_shadow="0 24px 60px rgba(15,26,51,0.18)",
        width="100%",
        min_height="280px",
        justify_content="center",
    )
    hero = rx.box(
        rx.grid(
            rx.vstack(
                rx.text("SERVIÇOS & ALFAIATARIA", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.14em"),
                rx.heading("Vista a peça. Sinta a diferença.", font_family=DISPLAY, font_size=["2.4rem", "3.4rem", "4rem"], color=CHALK, line_height="1.02", letter_spacing="-0.04em"),
                rx.text("Ajustes, reparos e transformações para que as suas roupas acompanhem a vida como ela é.", color="rgba(248,249,250,0.76)", font_size=["0.98rem", "1.08rem"], line_height="1.7", max_width="580px"),
                rx.hstack(
                    rx.link(rx.hstack(rx.text("Criar meu espaço"), rx.icon("arrow-right", size=17), spacing="2", align="center"), href="/cadastro", color=INK, background=THREAD, padding="0.85rem 1.15rem", border_radius="999px", font_weight="700"),
                    rx.link("Como funciona", href="/como-funciona", color=CHALK, font_weight="700", padding="0.8rem 0.4rem"),
                    rx.link("Solicitar um ajuste", href="/servicos/solicitar", color=CHALK, font_weight="700", padding="0.8rem 0.4rem"),
                    spacing="3", align="center", flex_wrap="wrap",
                ),
                spacing="4", align_items="flex-start", width="100%",
            ),
            hero_visual,
            columns={"initial": "1", "lg": "1.15fr 0.85fr"}, spacing="6", align_items="center", width="100%", max_width="1180px", margin_x="auto",
        ),
        padding_y=["3.5rem", "5rem"], padding_x=["1.1rem", "2rem"],
        background=f"linear-gradient(145deg, {INK}, {DENIM})", width="100%",
    )
    catalog = rx.box(
        rx.vstack(
            rx.text("UM CUIDADO PARA CADA PEÇA", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
            rx.heading("O que uma boa alfaiataria pode fazer.", font_family=DISPLAY, font_size=["1.9rem", "2.6rem"], color=INK, text_align="center", letter_spacing="-0.03em"),
            rx.text("Comece entendendo a necessidade da peça. O melhor ajuste é aquele que respeita o tecido, o uso e o seu conforto.", color=MUTED, text_align="center", max_width="680px", line_height="1.65"),
            rx.grid(*service_cards, columns={"initial": "1", "sm": "2", "lg": "4"}, spacing="4", width="100%"),
            spacing="4", align_items="center", width="100%", max_width="1180px", margin_x="auto",
        ),
        class_name="osd-story-reveal", padding_y=["3.5rem", "5rem"], padding_x=["1.1rem", "2rem"], width="100%",
    )
    process = rx.box(
        rx.vstack(
            rx.text("UM PROCESSO MAIS CONSCIENTE", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
            rx.heading("Do primeiro olhar ao novo caimento.", font_family=DISPLAY, font_size=["1.9rem", "2.6rem"], color=CHALK, text_align="center"),
            rx.grid(*process_cards, columns={"initial": "1", "md": "3"}, spacing="4", width="100%"),
            spacing="4", align_items="center", width="100%", max_width="1180px", margin_x="auto",
        ),
        class_name="osd-story-reveal", padding_y=["3.5rem", "5rem"], padding_x=["1.1rem", "2rem"], background=INK, width="100%",
    )
    wardrobe = rx.box(
        rx.grid(
            rx.vstack(
                rx.text("COMECE PELO SEU ACERVO", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
                rx.heading("Qual peça merece uma nova chance?", font_family=DISPLAY, font_size=["1.9rem", "2.5rem"], color=INK, line_height="1.08"),
                rx.text("Organize suas roupas no armário digital e descubra quais delas podem ganhar um ajuste, um reparo ou uma combinação nova.", color=MUTED, line_height="1.7"),
                rx.link("Conhecer o armário digital →", href="/como-funciona", color=DENIM, font_weight="700"),
                spacing="3", align_items="flex-start",
            ),
            rx.center(rx.icon("shirt", size=56, color=DENIM), width="100%", min_height="220px", background="linear-gradient(145deg, #E8EAF0, #F5ECDD)", border_radius="24px"),
            columns={"initial": "1", "md": "1fr 0.8fr"}, spacing="5", align_items="center", width="100%", max_width="1120px", margin_x="auto",
        ),
        class_name="osd-story-reveal", padding_y=["3.5rem", "5rem"], padding_x=["1.1rem", "2rem"], width="100%",
    )
    return marketing_page_shell(hero, catalog, process, wardrobe, home_cta_banner())


def how_it_works_page() -> rx.Component:
    steps = [
        ("01", "Crie seu espaço", "Entre ou crie uma conta para reunir suas informações pessoais e seu guarda-roupa."),
        ("02", "Adicione suas peças", "Cadastre cada item com nome, categoria, cor e imagem para manter o acervo fácil de consultar."),
        ("03", "Monte seus looks", "Combine itens do armário, salve suas composições e organize quando quer usar cada uma."),
        ("04", "Continue explorando", "Acesse inspirações, acompanhe seus pedidos e descubra outras formas de cuidar do que veste."),
    ]
    step_cards = [
        rx.box(
            rx.hstack(
                rx.center(rx.text(number, font_family=DISPLAY, font_size="1.25rem", font_weight="800", color=INK), width="48px", height="48px", border_radius="16px", background=THREAD, flex_shrink="0"),
                rx.vstack(
                    rx.heading(title, font_family=DISPLAY, color=INK, font_size="1.15rem"),
                    rx.text(description, color=MUTED, font_size="0.9rem", line_height="1.65"),
                    spacing="2", align_items="flex-start", width="100%",
                ),
                spacing="4", align_items="flex-start", width="100%",
            ),
            background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding=["1.2rem", "1.5rem"], width="100%",
            box_shadow="0 12px 32px rgba(15,26,51,0.04)",
        )
        for number, title, description in steps
    ]
    preview = rx.box(
        rx.vstack(
            rx.hstack(rx.icon("layout-dashboard", size=17, color=THREAD), rx.text("PRÉVIA DO SEU ESPAÇO", color=THREAD, font_size="0.66rem", font_weight="800", letter_spacing="0.12em"), spacing="2", align="center"),
            rx.heading("Seu armário, com mais clareza.", color=CHALK, font_family=DISPLAY, font_size="1.45rem"),
            rx.hstack(
                rx.box(rx.icon("shirt", size=25, color=DENIM), width="72px", height="90px", background="#F3F0E8", border_radius="16px", display="grid", place_items="center"),
                rx.box(rx.icon("shirt", size=25, color=DENIM), width="72px", height="90px", background="#E8EAF0", border_radius="16px", display="grid", place_items="center"),
                rx.box(rx.icon("shirt", size=25, color=DENIM), width="72px", height="90px", background="#F4E4D2", border_radius="16px", display="grid", place_items="center"),
                spacing="3", flex_wrap="wrap",
            ),
            rx.hstack(rx.icon("calendar-days", size=17, color=THREAD), rx.text("Peças, looks e planos no mesmo lugar", color="rgba(248,249,250,0.74)", font_size="0.85rem"), spacing="2", align="center"),
            spacing="4", align_items="flex-start", width="100%",
        ),
        background=f"linear-gradient(145deg, {DENIM}, {INK})", border="1px solid rgba(233,162,59,0.24)", border_radius="26px", padding=["1.4rem", "1.8rem"], width="100%",
    )
    hero = rx.box(
        rx.grid(
            rx.vstack(
                rx.text("COMO FUNCIONA", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.14em"),
                rx.heading("Seu guarda-roupa, em movimento.", font_family=DISPLAY, font_size=["2.35rem", "3.3rem", "3.8rem"], color=CHALK, line_height="1.02", letter_spacing="-0.04em"),
                rx.text("O OSDROUPA transforma a rotina de vestir em um fluxo simples: organizar o que você tem, testar novas combinações e planejar seus próximos dias.", color="rgba(248,249,250,0.75)", font_size="1rem", line_height="1.7", max_width="600px"),
                rx.link("Começar agora →", href="/cadastro", color=INK, background=THREAD, padding="0.85rem 1.2rem", border_radius="999px", font_weight="700"),
                spacing="4", align_items="flex-start",
            ),
            preview,
            columns={"initial": "1", "lg": "1.08fr 0.92fr"}, spacing="6", align_items="center", width="100%", max_width="1180px", margin_x="auto",
        ),
        padding_y=["3.5rem", "5rem"], padding_x=["1.1rem", "2rem"], background=f"linear-gradient(145deg, {INK}, {DENIM})", width="100%",
    )
    workflow = rx.box(
        rx.vstack(
            rx.text("UM CAMINHO DE CADA VEZ", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
            rx.heading("Da primeira peça ao look planejado.", font_family=DISPLAY, font_size=["1.9rem", "2.55rem"], color=INK, text_align="center", letter_spacing="-0.03em"),
            rx.grid(*step_cards, columns={"initial": "1", "md": "2"}, spacing="4", width="100%"),
            spacing="4", align_items="center", width="100%", max_width="1120px", margin_x="auto",
        ),
        class_name="osd-story-reveal", padding_y=["3.5rem", "5rem"], padding_x=["1.1rem", "2rem"], width="100%",
    )
    final_section = rx.box(
        rx.vstack(
            rx.center(rx.icon("heart-handshake", size=28, color=THREAD), width="64px", height="64px", border_radius="20px", background="rgba(233,162,59,0.12)"),
            rx.heading("Feito para a sua vida real.", font_family=DISPLAY, font_size=["1.9rem", "2.5rem"], color=INK, text_align="center"),
            rx.text("Você não precisa organizar tudo de uma vez. Adicione uma peça, teste uma combinação e construa seu espaço aos poucos.", color=MUTED, max_width="650px", text_align="center", line_height="1.7"),
            rx.hstack(rx.link("Criar conta", href="/cadastro", color=INK, background=THREAD, padding="0.8rem 1.2rem", border_radius="999px", font_weight="700"), rx.link("Explorar a loja", href="/loja", color=DENIM, font_weight="700", padding="0.8rem"), spacing="3", flex_wrap="wrap", justify="center"),
            spacing="3", align="center", width="100%", max_width="900px", margin_x="auto",
        ),
        class_name="osd-story-reveal", padding_y=["3rem", "4.5rem"], padding_x=["1.1rem", "2rem"], width="100%",
    )
    return marketing_page_shell(hero, workflow, final_section)


def testimonials_page() -> rx.Component:
    prompts = [
        ("sun", "Manhãs mais leves", "Queremos saber se organizar suas peças ajudou a escolher o que vestir com mais tranquilidade."),
        ("sparkles", "Um estilo mais seu", "Conte quais combinações fizeram você redescobrir o seu jeito de se vestir."),
        ("leaf", "Peças com história", "Compartilhe como cuidar e reutilizar uma peça mudou a relação com o seu armário."),
    ]
    cards = [
        rx.box(
            rx.vstack(
                rx.center(rx.icon(icon_name, size=20, color=THREAD), width="48px", height="48px", border_radius="15px", background="rgba(233,162,59,0.13)"),
                rx.heading(title, font_family=DISPLAY, color=INK, font_size="1.12rem"),
                rx.text(description, color=MUTED, font_size="0.9rem", line_height="1.65"),
                spacing="3", align_items="flex-start", width="100%",
            ),
            background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.3rem", width="100%",
        )
        for icon_name, title, description in prompts
    ]
    hero = rx.box(
        rx.vstack(
            rx.box(rx.text("DEPOIMENTOS", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"), padding="0.45rem 0.8rem", background="rgba(233,162,59,0.12)", border="1px solid rgba(233,162,59,0.26)", border_radius="999px"),
            rx.heading("Cada armário tem uma história. A próxima pode ser a sua.", font_family=DISPLAY, font_size=["2.3rem", "3.3rem", "3.8rem"], color=CHALK, text_align="center", max_width="920px", line_height="1.04", letter_spacing="-0.04em"),
            rx.text("Queremos que este espaço seja feito de experiências verdadeiras, contadas por quem usa o OSDROUPA.", color="rgba(248,249,250,0.75)", font_size="1rem", text_align="center", max_width="660px", line_height="1.7"),
            spacing="4", align="center", width="100%", max_width="1040px", margin_x="auto",
        ),
        padding_y=["3.5rem", "5.5rem"], padding_x=["1.1rem", "2rem"], background=f"linear-gradient(145deg, {INK}, {DENIM})", width="100%",
    )
    community = rx.box(
        rx.grid(
            rx.vstack(
                rx.text("HISTÓRIAS DA COMUNIDADE", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
                rx.heading("Um espaço para relatos reais.", font_family=DISPLAY, color=INK, font_size=["1.8rem", "2.4rem"], line_height="1.08"),
                rx.text("Ainda estamos reunindo as primeiras experiências. Quando os relatos chegarem, eles serão publicados com autorização e sem inventar avaliações.", color=MUTED, line_height="1.7"),
                rx.hstack(rx.icon("badge-check", size=18, color=OK), rx.text("Transparência em cada história", color=OK, font_weight="700", font_size="0.88rem"), spacing="2", align="center"),
                spacing="3", align_items="flex-start",
            ),
            rx.box(
                rx.vstack(
                    rx.center(rx.icon("message-circle-heart", size=28, color=THREAD), width="68px", height="68px", border_radius="22px", background="rgba(233,162,59,0.12)"),
                    rx.heading("A sua experiência importa.", font_family=DISPLAY, color=CHALK, font_size="1.4rem", text_align="center"),
                    rx.text("Entre para conhecer a plataforma e, quando quiser, conte como ela faz parte da sua rotina.", color="rgba(248,249,250,0.7)", text_align="center", line_height="1.65"),
                    rx.link("Fazer parte da comunidade", href="/cadastro", color=INK, background=THREAD, padding="0.8rem 1.1rem", border_radius="999px", font_weight="700"),
                    spacing="3", align="center", width="100%",
                ),
                background=f"linear-gradient(145deg, {INK}, {DENIM})", border_radius="24px", padding=["1.4rem", "1.8rem"], width="100%",
            ),
            columns={"initial": "1", "lg": "1fr 0.8fr"}, spacing="5", align_items="center", width="100%", max_width="1120px", margin_x="auto",
        ),
        class_name="osd-story-reveal", padding_y=["3rem", "4.5rem"], padding_x=["1.1rem", "2rem"], width="100%",
    )
    listening = rx.box(
        rx.vstack(
            rx.text("O QUE GOSTARÍAMOS DE OUVIR", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
            rx.heading("O seu jeito de vestir tem voz.", font_family=DISPLAY, font_size=["1.9rem", "2.5rem"], color=INK, text_align="center"),
            rx.grid(*cards, columns={"initial": "1", "md": "3"}, spacing="4", width="100%"),
            spacing="4", align="center", width="100%", max_width="1120px", margin_x="auto",
        ),
        class_name="osd-story-reveal", padding_y=["2.5rem", "3.5rem"], padding_x=["1.1rem", "2rem"], width="100%",
    )
    testimony_wall = rx.box(
        rx.vstack(
            rx.text("RELATOS PUBLICADOS", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
            rx.cond(
                WardrobeLifeState.testimonials.length() > 0,
                rx.grid(rx.foreach(WardrobeLifeState.testimonials, lambda item: rx.box(
                    rx.vstack(rx.icon("quote", size=20, color=THREAD), rx.text(item["texto"], color=INK, line_height="1.75"), rx.text(item["nome"], color=MUTED, font_size="0.82rem", font_weight="700"), spacing="3", align_items="flex-start", width="100%"),
                    background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.3rem", width="100%",
                )), columns={"initial": "1", "md": "2", "lg": "3"}, spacing="4", width="100%"),
                rx.callout("Ainda não há relatos aprovados. Os próximos serão experiências reais enviadas pela comunidade.", icon="message-circle", color="amber", width="100%"),
            ),
            rx.cond(WardrobeLifeState.experience_error != "", rx.callout(WardrobeLifeState.experience_error, icon="triangle-alert", color="red", width="100%")),
            spacing="4", align_items="stretch", width="100%", max_width="1120px", margin_x="auto",
        ), class_name="osd-story-reveal", padding_y=["2rem", "3rem"], padding_x=["1.1rem", "2rem"], width="100%",
    )
    testimony_form = rx.box(
        rx.vstack(
            rx.heading("Conte uma experiência verdadeira", font_family=DISPLAY, color=INK, font_size=["1.5rem", "2rem"]),
            rx.text("Seu relato fica privado até a equipe revisar. Só publicamos com sua autorização, e você pode escolher aparecer como pessoa anônima.", color=MUTED, line_height="1.65"),
            rx.cond(
                AuthState.account_validated,
                rx.vstack(
                    rx.text_area(value=WardrobeLifeState.testimonial_text, on_change=WardrobeLifeState.set_testimonial_text, placeholder="O que você usou no OSDROUPA e como foi sua experiência?", width="100%", min_height="150px"),
                    rx.checkbox("Quero aparecer como pessoa anônima", checked=WardrobeLifeState.testimonial_anonymous, on_change=WardrobeLifeState.set_testimonial_anonymous),
                    rx.checkbox("Autorizo a publicação deste relato após revisão", checked=WardrobeLifeState.testimonial_consent, on_change=WardrobeLifeState.set_testimonial_consent),
                    rx.button("Enviar para revisão", on_click=WardrobeLifeState.submit_testimonial, background=INK, color=CHALK, border_radius="100px", font_weight="700"),
                    rx.cond(WardrobeLifeState.experience_notice != "", rx.callout(WardrobeLifeState.experience_notice, icon="info", color="green", width="100%")),
                    spacing="3", align_items="stretch", width="100%",
                ),
                rx.link("Entre na sua conta para enviar um relato", href="/login", color=DENIM, font_weight="700"),
            ),
            rx.cond(WardrobeLifeState.my_testimonials.length() > 0, rx.vstack(rx.text("SEUS ENVIOS", color=MUTED, font_size="0.72rem", font_weight="800", letter_spacing="0.1em"), rx.foreach(WardrobeLifeState.my_testimonials, lambda item: rx.hstack(rx.text(item["status"], color=INK, font_weight="700"), rx.spacer(), rx.text(item["created_at"], color=MUTED, font_size="0.8rem"), width="100%", padding="0.75rem", background="#F7F5EF", border_radius="12px")), spacing="2", width="100%", align_items="stretch")),
            spacing="3", width="100%", align_items="stretch",
        ), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding=["1.2rem", "1.6rem"], width="100%", max_width="900px", margin_x="auto",
    )
    return marketing_page_shell(hero, community, listening, testimony_wall, testimony_form)


def wardrobe_life_shell(eyebrow: str, title: str, subtitle: str, body: rx.Component) -> rx.Component:
    experience_links = [
        ("Look do dia", "/look-do-dia"),
        ("Histórico de uso", "/historico-uso"),
        ("Mala", "/malas"),
        ("Provador", "/provador"),
        ("Fidelidade", "/fidelidade"),
        ("Alfaiataria", "/servicos/solicitar"),
        ("Privacidade", "/privacidade"),
    ]
    experience_nav = rx.flex(
        *[
            rx.link(label, href=href, color=DENIM, background="#FFFFFF", border="1px solid rgba(15,26,51,.1)", border_radius="999px", padding="0.55rem 0.85rem", font_size="0.8rem", font_weight="700", _hover={"border_color": THREAD, "transform": "translateY(-1px)"})
            for label, href in experience_links
        ],
        gap="2", flex_wrap="wrap", width="100%",
    )
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.vstack(rx.text(eyebrow.upper(), color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"), rx.heading(title, font_family=DISPLAY, color=INK, font_size=["2rem", "2.65rem", "3.2rem"], line_height="1.05"), rx.text(subtitle, color=MUTED, font_size=["0.92rem", "1rem"], line_height="1.7", max_width="720px"), spacing="2", align_items="flex-start", width="100%"),
            experience_nav,
            rx.cond(WardrobeLifeState.experience_error != "", rx.callout(WardrobeLifeState.experience_error, icon="triangle-alert", color="red", width="100%")),
            rx.cond(WardrobeLifeState.experience_notice != "", rx.callout(WardrobeLifeState.experience_notice, icon="info", color="green", width="100%")),
            body, spacing="5", width="100%", max_width="1120px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"], align_items="stretch",
        ), width="100%"), min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def life_garment_card(item: dict) -> rx.Component:
    image = rx.cond(item["image_url"] != "", rx.image(src=item["image_url"], alt=item["name"], width="100%", height="200px", object_fit="cover", border_radius="16px"), rx.center(rx.icon("shirt", size=44, color=DENIM), width="100%", height="200px", background="linear-gradient(145deg,#E8EAF0,#F3F0E8)", border_radius="16px"))
    return rx.box(rx.vstack(image, rx.text(item["name"], color=INK, font_weight="700"), rx.text(item["category"], color=MUTED, font_size="0.8rem"), spacing="2", width="100%", align_items="flex-start"), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="0.8rem", width="100%")


def _weather_stat(label: str, value) -> rx.Component:
    return rx.vstack(rx.text(label, color=MUTED, font_size="0.72rem", font_weight="700", letter_spacing="0.06em"), rx.text(value, color=INK, font_weight="700"), spacing="0", align_items="flex-start")


def weather_context_card() -> rx.Component:
    ctx = WardrobeLifeState.weather_context
    forecast = rx.vstack(
        rx.hstack(
            rx.icon("cloud-sun", size=22, color=THREAD),
            rx.heading(f"Clima agora em {ctx['cidade']}/{ctx['uf']}", font_family=DISPLAY, color=INK, font_size="1.15rem"),
            spacing="2", align="center", flex_wrap="wrap",
        ),
        rx.text(ctx["condicao"], " · ", ctx["regiao"], " · ", ctx["estacao"], " · ", ctx["periodo"], color=MUTED, font_size="0.86rem"),
        rx.grid(
            _weather_stat("TEMPERATURA", f"{ctx['temperatura']} °C"),
            _weather_stat("SENSAÇÃO", f"{ctx['sensacao']} °C"),
            _weather_stat("MÍN / MÁX", f"{ctx['minima']}° / {ctx['maxima']}°"),
            _weather_stat("CHUVA", f"{ctx['chuva_prob']}%"),
            _weather_stat("UMIDADE", f"{ctx['umidade']}%"),
            _weather_stat("UV MÁX", ctx["uv_max"]),
            columns={"initial": "3", "md": "6"}, spacing="3", width="100%",
        ),
        rx.text(
            "Fonte: Open-Meteo · atualizado às ", ctx["hora_local"], " (horário local)",
            rx.cond(ctx["manual"] != "", " · clima escolhido manualmente", ""),
            color=MUTED, font_size="0.74rem",
        ),
        spacing="2", width="100%", align_items="stretch",
    )
    search = rx.hstack(
        rx.input(placeholder="Outra cidade (ex.: Curitiba/PR)", value=WardrobeLifeState.weather_city_query, on_change=WardrobeLifeState.set_weather_city_query, max_length=80, flex="1"),
        rx.button("Ver clima", on_click=WardrobeLifeState.search_weather_city, loading=WardrobeLifeState.weather_loading, variant="outline", border_radius="100px"),
        spacing="2", width="100%",
    )
    return rx.box(
        rx.vstack(
            rx.cond(
                WardrobeLifeState.weather_loading & ~WardrobeLifeState.has_weather,
                rx.hstack(rx.spinner(), rx.text("Consultando a previsão...", color=MUTED), spacing="2", align="center"),
                rx.cond(WardrobeLifeState.has_weather, forecast, rx.fragment()),
            ),
            rx.cond(WardrobeLifeState.weather_notice != "", rx.text(WardrobeLifeState.weather_notice, color=MUTED, font_size="0.86rem")),
            search,
            spacing="3", width="100%", align_items="stretch",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding="1.3rem", width="100%",
    )


def ai_piece_row(piece: LookPiece) -> rx.Component:
    thumb = rx.cond(
        piece.imagem_url != "",
        rx.image(src=piece.imagem_url, alt=piece.nome, width="56px", height="56px", object_fit="cover", border_radius="12px", flex_shrink="0"),
        rx.center(rx.icon("shirt", size=22, color=DENIM), width="56px", height="56px", background="linear-gradient(145deg,#E8EAF0,#F3F0E8)", border_radius="12px", flex_shrink="0"),
    )
    badge_color = rx.match(piece.origem, ("armario", "green"), ("catalogo", "amber"), "gray")
    return rx.hstack(
        thumb,
        rx.vstack(
            rx.hstack(
                rx.text(piece.nome, color=INK, font_weight="700", font_size="0.9rem"),
                rx.badge(piece.origem_label, color_scheme=badge_color, variant="soft", radius="full"),
                spacing="2", align="center", flex_wrap="wrap",
            ),
            rx.text(piece.papel_label, rx.cond(piece.descricao != "", " · ", ""), piece.descricao, color=MUTED, font_size="0.8rem"),
            rx.cond(piece.origem == "catalogo", rx.link("Ver na loja", href=f"/produto?id={piece.ref}", color=DENIM, font_size="0.78rem", font_weight="700")),
            spacing="1", align_items="flex-start",
        ),
        spacing="3", align="start", width="100%",
    )


def _score_chip(label: str, value) -> rx.Component:
    return rx.vstack(rx.text(label, color=MUTED, font_size="0.68rem", font_weight="700", letter_spacing="0.05em"), rx.text(value, "/5", color=INK, font_weight="700", font_size="0.9rem"), spacing="0", align_items="center")


def review_summary(review: LookReview) -> rx.Component:
    """Notas, pontos fortes e problemas de uma avaliação (Change 026)."""
    return rx.vstack(
        rx.hstack(
            rx.center(rx.text(review.nota_geral, color=CHALK, font_weight="800", font_size="1.05rem"), background=INK, border_radius="14px", min_width="52px", height="52px", flex_shrink="0"),
            rx.grid(
                _score_chip("CLIMA", review.nota_clima), _score_chip("HARMONIA", review.nota_harmonia), _score_chip("OCASIÃO", review.nota_ocasiao),
                _score_chip("CONFORTO", review.nota_conforto), _score_chip("ESTILO", review.nota_estilo),
                columns={"initial": "3", "sm": "5"}, spacing="2", width="100%",
            ),
            spacing="3", align="center", width="100%",
        ),
        rx.cond(review.pontos_fortes != "", rx.text(rx.text.strong("Pontos fortes: "), review.pontos_fortes, color=INK, font_size="0.84rem", line_height="1.6")),
        rx.cond(
            review.problemas.length() > 0,
            rx.vstack(
                rx.foreach(review.problemas, lambda problem: rx.hstack(rx.icon("circle-alert", size=14, color=THREAD, flex_shrink="0", margin_top="3px"), rx.text(problem, color=INK, font_size="0.84rem"), spacing="2", align="start")),
                spacing="1", width="100%",
            ),
        ),
        spacing="2", width="100%", align_items="stretch",
    )


def swap_description(swap: LookSwap) -> rx.Component:
    return rx.vstack(
        rx.text(
            rx.cond(swap.sai_nome != "", rx.fragment(swap.sai_nome, " → "), "Acrescentar: "),
            rx.text.strong(swap.entra.nome),
            color=INK, font_size="0.84rem",
        ),
        rx.hstack(rx.badge(swap.entra.origem_label, color_scheme=rx.match(swap.entra.origem, ("armario", "green"), ("catalogo", "amber"), "gray"), variant="soft", radius="full"), rx.text(swap.motivo, color=MUTED, font_size="0.78rem"), spacing="2", align="center", flex_wrap="wrap"),
        spacing="1", align_items="flex-start", flex="1",
    )


def ai_swap_row(swap: LookSwap, proposal_id) -> rx.Component:
    return rx.hstack(
        swap_description(swap),
        rx.cond(swap.aplicavel, rx.button("Aplicar", on_click=WardrobeLifeState.apply_ai_swap(proposal_id, swap.id), variant="outline", size="1", border_radius="100px")),
        spacing="2", align="start", width="100%",
    )


def look_board_tile(piece: LookPiece) -> rx.Component:
    return rx.box(
        rx.cond(
            piece.imagem_url != "",
            rx.image(src=piece.imagem_url, alt=piece.nome, width="100%", height="100%", object_fit="contain"),
            rx.center(rx.vstack(rx.icon("shirt", size=26, color=DENIM), rx.text(piece.nome, color=MUTED, font_size="0.7rem", text_align="center"), spacing="1", align="center"), width="100%", height="100%", padding="0.4rem"),
        ),
        position="relative", aspect_ratio="1", background="#FFFFFF", border_radius="12px", overflow="hidden",
        border=rx.cond(piece.origem == "armario", "1px solid rgba(15,26,51,0.08)", "1px dashed rgba(233,162,59,0.7)"),
    )


def look_visual(proposal: LookProposal) -> rx.Component:
    """Composição com as fotos reais das peças e, opcionalmente, a imagem gerada pelo Google (Change 027)."""
    generated = rx.vstack(
        rx.image(src=rx.get_upload_url(proposal.imagem_gerada), alt=f"Imagem gerada por IA do look {proposal.nome}", width="100%", border_radius="16px"),
        rx.text("Imagem gerada por IA (Google Gemini, com marca d'água SynthID). As peças podem diferir das reais; confira o quadro com as fotos.", color=MUTED, font_size="0.72rem"),
        spacing="1", width="100%",
    )
    return rx.vstack(
        rx.cond(proposal.imagem_gerada != "", generated),
        rx.grid(rx.foreach(proposal.pecas, look_board_tile), columns="4", spacing="2", width="100%", background="#F7F5EF", padding="0.5rem", border_radius="16px"),
        rx.cond(
            WardrobeLifeState.image_ai_enabled & (proposal.imagem_gerada == ""),
            rx.button(
                rx.icon("image", size=15), "Gerar imagem do look",
                on_click=WardrobeLifeState.generate_look_image(proposal.id),
                loading=WardrobeLifeState.image_loading_id == proposal.id,
                disabled=(WardrobeLifeState.image_loading_id != "") & (WardrobeLifeState.image_loading_id != proposal.id),
                variant="soft", size="2", border_radius="100px",
            ),
        ),
        rx.cond(WardrobeLifeState.image_loading_id == proposal.id, rx.text("Gerando a imagem; pode levar até um minuto.", color=MUTED, font_size="0.76rem")),
        spacing="2", width="100%", align_items="stretch",
    )


AI_FEEDBACK_REASONS = ["Não combina comigo", "Não serve para o clima", "Não serve para a ocasião", "Pouco confortável", "Já uso muito essas peças", "Outro motivo"]


def ai_feedback_bar(proposal: LookProposal) -> rx.Component:
    given = WardrobeLifeState.ai_feedback[proposal.id]
    return rx.cond(
        WardrobeLifeState.ai_feedback.contains(proposal.id),
        rx.text(rx.cond(given == "positivo", "👍 Você gostou deste look.", "👎 Anotado: vamos evitar algo assim."), color=MUTED, font_size="0.82rem"),
        rx.vstack(
            rx.hstack(
                rx.text("Este look combina com você?", color=INK, font_size="0.84rem", font_weight="600"),
                rx.button("👍", on_click=WardrobeLifeState.send_ai_feedback(proposal.id, "positivo", ""), variant="soft", size="1", aria_label="Gostei"),
                rx.button("👎", on_click=WardrobeLifeState.open_ai_feedback(proposal.id), variant="soft", size="1", aria_label="Não gostei"),
                spacing="2", align="center", flex_wrap="wrap",
            ),
            rx.cond(
                WardrobeLifeState.ai_feedback_open_id == proposal.id,
                rx.hstack(
                    rx.foreach(AI_FEEDBACK_REASONS, lambda reason: rx.button(reason, on_click=WardrobeLifeState.send_ai_feedback(proposal.id, "negativo", reason), variant="outline", size="1", border_radius="100px")),
                    spacing="2", flex_wrap="wrap",
                ),
            ),
            spacing="2", width="100%", align_items="start",
        ),
    )


def ai_proposal_card(proposal: LookProposal) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading(proposal.nome, font_family=DISPLAY, color=INK, font_size="1.1rem"),
                rx.cond(proposal.conforto != "", rx.badge(proposal.conforto, variant="outline", radius="full")),
                justify="between", align="center", width="100%", flex_wrap="wrap", spacing="2",
            ),
            rx.cond(proposal.descricao != "", rx.text(proposal.descricao, color=INK, font_size="0.88rem", line_height="1.6")),
            look_visual(proposal),
            rx.cond(proposal.precisa_pecas, rx.callout("Seu armário ainda não cobre este look sozinho; ele foi completado com sugestões.", icon="info", color="amber", size="1", width="100%")),
            rx.vstack(rx.foreach(proposal.pecas, ai_piece_row), spacing="2", width="100%"),
            rx.cond(proposal.paleta != "", rx.text(rx.text.strong("Cores: "), proposal.paleta, color=MUTED, font_size="0.82rem")),
            rx.cond(proposal.tecidos != "", rx.text(rx.text.strong("Tecidos: "), proposal.tecidos, color=MUTED, font_size="0.82rem")),
            rx.cond(
                proposal.acessorios_sugeridos.length() > 0,
                rx.vstack(
                    rx.text("Acessórios sugeridos (opcionais)", color=INK, font_weight="700", font_size="0.82rem"),
                    rx.hstack(rx.foreach(proposal.acessorios_sugeridos, lambda tip: rx.badge(tip, variant="soft", radius="full", color_scheme="gray")), spacing="2", flex_wrap="wrap"),
                    spacing="1", width="100%", align_items="start",
                ),
            ),
            rx.cond(proposal.justificativa_clima != "", rx.text(rx.text.strong("Clima: "), proposal.justificativa_clima, color=INK, font_size="0.85rem", line_height="1.6")),
            rx.cond(proposal.justificativa_estilo != "", rx.text(rx.text.strong("Estilo e ocasião: "), proposal.justificativa_estilo, color=INK, font_size="0.85rem", line_height="1.6")),
            rx.cond(
                proposal.avaliacao.disponivel,
                rx.box(
                    rx.vstack(
                        rx.text("Avaliação", color=INK, font_weight="700", font_size="0.9rem"),
                        review_summary(proposal.avaliacao),
                        rx.cond(
                            proposal.avaliacao.trocas.length() > 0,
                            rx.vstack(
                                rx.text("Como melhorar", color=INK, font_weight="700", font_size="0.84rem"),
                                rx.foreach(proposal.avaliacao.trocas, lambda swap: ai_swap_row(swap, proposal.id)),
                                spacing="2", width="100%",
                            ),
                        ),
                        spacing="2", width="100%", align_items="stretch",
                    ),
                    background="#F7F5EF", border_radius="16px", padding="0.85rem", width="100%",
                ),
            ),
            rx.cond(
                (proposal.fonte == "ia") & WardrobeLifeState.ai_personalization_on,
                ai_feedback_bar(proposal),
            ),
            rx.hstack(
                rx.button("Salvar em Meus Looks", on_click=WardrobeLifeState.save_ai_proposal(proposal.id), background=THREAD, color=INK, border_radius="100px", font_weight="700", size="2"),
                rx.cond(
                    WardrobeLifeState.ai_saved_inspirations.contains(proposal.id),
                    rx.link(rx.hstack(rx.icon("bookmark-check", size=15), rx.text("Nas suas inspirações"), spacing="1", align="center"), href="/inspiracao", color=DENIM, font_weight="700", font_size="0.85rem"),
                    rx.button(rx.icon("bookmark", size=15), "Guardar inspiração", on_click=WardrobeLifeState.save_ai_inspiration(proposal.id), variant="outline", size="2", border_radius="100px"),
                ),
                spacing="2", flex_wrap="wrap", align="center",
            ),
            spacing="3", width="100%", align_items="stretch",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding="1.2rem", width="100%",
    )


def ai_stylist_section() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                rx.hstack(rx.icon("sparkles", size=20, color=THREAD), rx.heading("Estilista com IA", font_family=DISPLAY, color=INK, font_size="1.3rem"), spacing="2", align="center"),
                rx.text("Looks completos com justificativa, usando o clima acima, a ocasião, seu estilo e as peças disponíveis no armário.", color=MUTED, font_size="0.88rem"),
                _label("Algo a considerar? (opcional)"),
                rx.input(placeholder="Ex.: reunião com cliente, vou de metrô", value=WardrobeLifeState.ai_note, on_change=WardrobeLifeState.set_ai_note, max_length=stylist.MAX_NOTE_LENGTH, width="100%"),
                rx.button(rx.icon("sparkles", size=16), "Gerar looks", on_click=WardrobeLifeState.generate_ai_looks, loading=WardrobeLifeState.ai_loading, background=INK, color=CHALK, border_radius="100px", font_weight="700"),
                rx.cond(WardrobeLifeState.ai_loading, rx.text("Montando as combinações; isso pode levar alguns segundos.", color=MUTED, font_size="0.8rem")),
                spacing="2", width="100%", align_items="stretch",
            ),
            background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding="1.3rem", width="100%",
        ),
        rx.cond(WardrobeLifeState.ai_error != "", rx.callout(WardrobeLifeState.ai_error, icon="triangle-alert", color="red", width="100%")),
        rx.cond(WardrobeLifeState.ai_notice != "", rx.callout(WardrobeLifeState.ai_notice, icon="info", width="100%")),
        rx.cond(
            WardrobeLifeState.ai_proposals.length() > 0,
            rx.grid(rx.foreach(WardrobeLifeState.ai_proposals, ai_proposal_card), columns={"initial": "1", "md": "2"}, spacing="3", width="100%"),
        ),
        spacing="3", width="100%", align_items="stretch",
    )


def daily_look_page() -> rx.Component:
    controls = rx.box(rx.vstack(rx.heading("Seu contexto", font_family=DISPLAY, color=INK, font_size="1.3rem"), rx.grid(rx.vstack(_label("Clima previsto"), rx.select(["Quente", "Ameno", "Frio", "Chuvoso"], value=WardrobeLifeState.daily_weather, on_change=WardrobeLifeState.set_daily_weather, width="100%"), spacing="1", width="100%", align_items="stretch"), rx.vstack(_label("Ocasião"), rx.select(LOOK_OCCASIONS, value=WardrobeLifeState.daily_occasion, on_change=WardrobeLifeState.set_daily_occasion, width="100%"), spacing="1", width="100%", align_items="stretch"), columns={"initial":"1","sm":"2"}, spacing="3", width="100%"), rx.button("Criar combinação", on_click=WardrobeLifeState.load_daily_look, loading=WardrobeLifeState.experience_loading, background=INK, color=CHALK, border_radius="100px", font_weight="700"), spacing="3", width="100%", align_items="stretch"), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding="1.3rem", width="100%")
    results = rx.cond(WardrobeLifeState.daily_suggestions.length() > 0, rx.vstack(rx.grid(rx.foreach(WardrobeLifeState.daily_suggestions, life_garment_card), columns={"initial":"1","sm":"2","lg":"4"}, spacing="3", width="100%"), rx.hstack(rx.button("Salvar em Meus Looks", on_click=WardrobeLifeState.save_daily_look, background=THREAD, color=INK, border_radius="100px", font_weight="700"), rx.link("Planejar no calendário", href="/calendario", color=DENIM, font_weight="700"), spacing="4", flex_wrap="wrap"), spacing="3", width="100%"), rx.center(rx.vstack(rx.icon("shirt", size=34, color=DENIM), rx.text("Seu armário ainda precisa de peças para sugerir um look.", color=MUTED), rx.link("Cadastrar peças", href="/armario", color=DENIM, font_weight="700"), spacing="3", align="center"), width="100%", min_height="170px", background="#FFFFFF", border_radius="20px"))
    return wardrobe_life_shell("Estilo para hoje", "Uma combinação começa no seu armário.", "A previsão real da cidade do seu endereço padrão sugere o clima; você pode trocar a cidade ou ajustar o clima manualmente. A sugestão usa as peças disponíveis que você cadastrou.", rx.vstack(weather_context_card(), controls, ai_stylist_section(), rx.cond(WardrobeLifeState.experience_notice != "", rx.text(WardrobeLifeState.experience_notice, color=MUTED)), results, spacing="4", width="100%", align_items="stretch"))


def loyalty_page() -> rx.Component:
    tier_cards = [
        ("Começo", "0 pontos", "Sua jornada começa com o primeiro desafio.", "circle"),
        ("Fio", "25 pontos", "Primeiro marco de consistência.", "sparkles"),
        ("Trama", "60 pontos", "Mais escolhas de reuso registradas.", "layers-3"),
        ("Ateliê", "100 pontos", "Uma rotina de cuidado em construção.", "scissors"),
        ("Ícone", "160 pontos", "Seu acervo, cuidado com intenção.", "crown"),
    ]
    cards = [
        rx.box(
            rx.vstack(
                rx.hstack(rx.icon(icon, size=22, color=THREAD), rx.spacer(), rx.cond(level == WardrobeLifeState.loyalty_level, rx.badge("Seu nível", color_scheme="green", variant="soft"), rx.box(display="none")), width="100%"),
                rx.heading(level, font_family=DISPLAY, color=INK, font_size="1.12rem"),
                rx.text(points, color=DENIM, font_weight="800"),
                rx.text(description, color=MUTED, font_size="0.85rem", line_height="1.55"),
                spacing="2", width="100%", align_items="flex-start",
            ),
            background=rx.cond(level == WardrobeLifeState.loyalty_level, "#FFF9EE", "#FFFFFF"),
            border=rx.cond(level == WardrobeLifeState.loyalty_level, "1px solid rgba(233,162,59,0.55)", "1px solid rgba(15,26,51,0.08)"),
            border_radius="18px", padding="1.1rem",
        )
        for level, points, description, icon in tier_cards
    ]
    hero_stats = rx.grid(
        rx.box(rx.vstack(rx.text("PONTOS DE ESTILO", color=MUTED, font_size="0.68rem", font_weight="800", letter_spacing="0.1em"), rx.text(WardrobeLifeState.loyalty_points, color=INK, font_family=DISPLAY, font_size="2.2rem", font_weight="800"), rx.text("Pontos pessoais", color=MUTED, font_size="0.78rem"), spacing="1"), background="#FFFFFF", border_radius="18px", padding="1.2rem"),
        rx.box(rx.vstack(rx.text("NÍVEL ATUAL", color=MUTED, font_size="0.68rem", font_weight="800", letter_spacing="0.1em"), rx.text(WardrobeLifeState.loyalty_level, color=INK, font_family=DISPLAY, font_size="2rem", font_weight="800"), rx.text("Próximo: " + WardrobeLifeState.loyalty_next_level, color=DENIM, font_size="0.82rem", font_weight="700"), spacing="1"), background="#FFFFFF", border_radius="18px", padding="1.2rem"),
        rx.box(rx.vstack(rx.text("DESAFIOS CONCLUÍDOS", color=MUTED, font_size="0.68rem", font_weight="800", letter_spacing="0.1em"), rx.text(WardrobeLifeState.loyalty_completed.to_string() + "/" + WardrobeLifeState.loyalty_challenge_total.to_string(), color=INK, font_family=DISPLAY, font_size="2.2rem", font_weight="800"), rx.text("Cada marco é registrado uma única vez", color=MUTED, font_size="0.78rem"), spacing="1"), background="#FFFFFF", border_radius="18px", padding="1.2rem"),
        columns={"initial": "1", "md": "3"}, spacing="3", width="100%",
    )
    progression = rx.box(
        rx.vstack(
            rx.hstack(rx.vstack(rx.heading("Seu próximo marco", font_family=DISPLAY, color=INK, font_size="1.3rem"), rx.text("Avance no seu ritmo, cuidando e redescobrindo seu acervo.", color=MUTED, font_size="0.86rem"), spacing="1", align_items="flex-start"), rx.spacer(), rx.badge(WardrobeLifeState.loyalty_next_level, color_scheme="amber", variant="soft", size="2"), width="100%", align="center", flex_wrap="wrap"),
            rx.hstack(rx.text(WardrobeLifeState.loyalty_tier_progress.to_string() + "%", color=INK, font_weight="800"), rx.spacer(), rx.text(rx.cond(WardrobeLifeState.loyalty_points_to_next > 0, WardrobeLifeState.loyalty_points_to_next.to_string() + " pontos para avançar", "Nível máximo alcançado"), color=MUTED, font_size="0.84rem"), width="100%"),
            rx.box(rx.box(width=WardrobeLifeState.loyalty_tier_progress.to_string() + "%", height="100%", background=f"linear-gradient(90deg, {THREAD}, #F3C46F)", border_radius="999px", transition="width 420ms ease"), width="100%", height="12px", background="rgba(15,26,51,0.08)", border_radius="999px", overflow="hidden", role="progressbar", aria_label="Progresso até o próximo nível"),
            rx.text("Os pontos representam participação e não podem ser convertidos em dinheiro, desconto ou saldo de compra.", color=MUTED, font_size="0.78rem"),
            spacing="3", width="100%", align_items="stretch",
        ), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.25rem", width="100%",
    )
    history_card = rx.box(
        rx.vstack(
            rx.hstack(rx.vstack(rx.heading("Sua jornada", font_family=DISPLAY, color=INK, font_size="1.3rem"), rx.text("Desafios concluídos e pontos registrados na sua conta.", color=MUTED, font_size="0.84rem"), spacing="1", align_items="flex-start"), rx.spacer(), rx.link("Ver desafios", href="/desafios", color=DENIM, font_weight="700"), width="100%", align="center", flex_wrap="wrap"),
            rx.cond(
                WardrobeLifeState.loyalty_history.length() > 0,
                rx.vstack(
                    rx.foreach(WardrobeLifeState.loyalty_history, lambda item: rx.hstack(rx.center(rx.icon("check", size=15, color=OK), width="34px", height="34px", background="#EAF4EE", border_radius="11px"), rx.vstack(rx.text(item["titulo"], color=INK, font_weight="700"), rx.text(item["concluido_em"], color=MUTED, font_size="0.75rem"), spacing="0", align_items="flex-start"), rx.spacer(), rx.badge("+" + item["pontos"] + " pts", color_scheme="amber", variant="soft"), width="100%", align="center", padding="0.75rem 0", border_bottom="1px solid rgba(15,26,51,0.06)")),
                    spacing="1", width="100%",
                ),
                rx.center(rx.vstack(rx.icon("sparkles", size=28, color=THREAD), rx.text("Seu primeiro marco começa com um desafio.", color=MUTED, text_align="center"), rx.link("Escolher desafio", href="/desafios", color=DENIM, font_weight="700"), spacing="2", align="center"), width="100%", min_height="120px"),
            ),
            spacing="3", width="100%", align_items="stretch",
        ), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.25rem", width="100%",
    )
    body = rx.vstack(
        hero_stats,
        progression,
        rx.vstack(rx.hstack(rx.vstack(rx.heading("Marcos de estilo", font_family=DISPLAY, color=INK, font_size="1.35rem"), rx.text("Cada nível reconhece uma etapa da sua jornada.", color=MUTED, font_size="0.85rem"), spacing="1", align_items="flex-start"), rx.spacer(), rx.link("Explorar desafios", href="/desafios", background=INK, color=CHALK, padding="0.75rem 1rem", border_radius="100px", font_weight="700"), width="100%", align="center", flex_wrap="wrap"), rx.grid(*cards, columns={"initial": "1", "sm": "2", "lg": "3", "xl": "5"}, spacing="3", width="100%"), spacing="3", width="100%", align_items="stretch"),
        history_card,
        rx.callout("Os desafios são concluídos por confirmação da própria pessoa. A fidelidade do OSDROUPA é feita de marcos e reconhecimento: pontos não são dinheiro, desconto nem saldo resgatável.", icon="sparkles", color="amber", width="100%"),
        rx.hstack(rx.link("Ver meu armário", href="/armario", color=DENIM, font_weight="700"), rx.link("Registrar uso de uma peça", href="/historico-uso", color=DENIM, font_weight="700"), spacing="4", flex_wrap="wrap"),
        spacing="4", width="100%", align_items="stretch",
    )
    return wardrobe_life_shell("Fidelidade OSDROUPA", "Cada desafio conta uma história.", "Acompanhe os pontos pessoais, os níveis e as pequenas escolhas de cuidado e reuso que você já concluiu.", body)


def usage_history_page() -> rx.Component:
    def usage_card(item: dict) -> rx.Component:
        return rx.box(rx.hstack(rx.vstack(rx.text(item["nome"], color=INK, font_weight="700"), rx.text(item["categoria"] + " · " + item["usos"] + " usos", color=MUTED, font_size="0.84rem"), rx.text(rx.cond(item["custo_por_uso"] != "", "Custo por uso: R$ " + item["custo_por_uso"], "Informe um valor no cadastro para calcular o custo por uso."), color=DENIM, font_size="0.82rem"), spacing="1", align_items="flex-start"), rx.spacer(), rx.button("Usei hoje", on_click=WardrobeLifeState.record_wear(item["id"]), background=THREAD, color=INK, border_radius="100px", font_weight="700"), width="100%", align="center", flex_wrap="wrap"), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1rem", width="100%")
    return wardrobe_life_shell("Cuidado e reuso", "Veja as peças que acompanham seus dias.", "Registre o uso e descubra quais roupas você redescobriu. O custo por uso aparece apenas para peças com valor de compra cadastrado.", rx.vstack(rx.cond(WardrobeLifeState.history_items.length() > 0, rx.vstack(rx.foreach(WardrobeLifeState.history_items, usage_card), spacing="3", width="100%"), rx.callout("Cadastre peças no armário para acompanhar o uso.", icon="shirt", color="amber", width="100%")), rx.heading("Registros recentes", font_family=DISPLAY, color=INK, font_size="1.3rem"), rx.cond(WardrobeLifeState.wear_events.length() > 0, rx.vstack(rx.foreach(WardrobeLifeState.wear_events, lambda item: rx.hstack(rx.text(item["peca"], color=INK, font_weight="600"), rx.spacer(), rx.text(item["worn_on"] + " · " + item["occasion"], color=MUTED, font_size="0.82rem"), width="100%", padding="0.8rem", background="#FFFFFF", border_radius="12px")), spacing="2", width="100%"), rx.text("Seus próximos usos registrados aparecem aqui.", color=MUTED)), spacing="3", width="100%", align_items="stretch"))


def packing_item_option(item: dict) -> rx.Component:
    return rx.button(rx.hstack(rx.icon(rx.cond(item["selected"] == "true", "check-circle-2", "circle"), size=17), rx.text(item["name"] + " · " + item["category"]), spacing="2"), on_click=WardrobeLifeState.toggle_packing_item(item["id"]), background=rx.cond(item["selected"] == "true", "rgba(233,162,59,.18)", "#FFFFFF"), color=INK, border="1px solid rgba(15,26,51,.1)", border_radius="14px", padding="0.8rem", width="100%", justify_content="flex-start")


def packing_page() -> rx.Component:
    form = rx.box(rx.vstack(rx.heading("Planeje uma mala", font_family=DISPLAY, color=INK, font_size="1.3rem"), rx.grid(field("Nome da viagem", value=WardrobeLifeState.packing_name, on_change=WardrobeLifeState.set_packing_name, placeholder="Fim de semana na serra"), field("Destino", value=WardrobeLifeState.packing_destination, on_change=WardrobeLifeState.set_packing_destination, placeholder="Campos do Jordão"), rx.vstack(_label("Ocasião principal"), rx.select(LOOK_OCCASIONS, value=WardrobeLifeState.packing_occasion, on_change=WardrobeLifeState.set_packing_occasion, width="100%"), spacing="1", width="100%", align_items="stretch"), rx.vstack(_label("De"), rx.input(type="date", value=WardrobeLifeState.packing_start, on_change=WardrobeLifeState.set_packing_start, **INPUT_STYLE), spacing="1", width="100%", align_items="stretch"), rx.vstack(_label("Até"), rx.input(type="date", value=WardrobeLifeState.packing_end, on_change=WardrobeLifeState.set_packing_end, **INPUT_STYLE), spacing="1", width="100%", align_items="stretch"), columns={"initial":"1","sm":"2"}, spacing="3", width="100%"), rx.text("Clima e previsão ficam por sua conta; a lista usa as peças escolhidas do armário.", color=MUTED, font_size="0.82rem"), rx.text("Selecione as peças para levar", color=INK, font_weight="700"), rx.grid(rx.foreach(WardrobeLifeState.packing_item_cards, packing_item_option), columns={"initial":"1","md":"2"}, spacing="2", width="100%"), rx.button("Salvar mala", on_click=WardrobeLifeState.save_packing_plan, background=INK, color=CHALK, border_radius="100px", font_weight="700"), spacing="3", width="100%", align_items="stretch"), background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="22px", padding="1.3rem", width="100%")
    plans = rx.cond(WardrobeLifeState.packing_plans.length() > 0, rx.grid(rx.foreach(WardrobeLifeState.packing_plans, lambda plan: rx.box(rx.vstack(rx.icon("briefcase", size=22, color=THREAD), rx.heading(plan["name"], font_family=DISPLAY, color=INK, font_size="1.1rem"), rx.text(plan["destination"], color=DENIM, font_weight="700"), rx.text(plan["start_date"] + " → " + plan["end_date"], color=MUTED, font_size="0.85rem"), rx.text(plan["occasion"], color=MUTED, font_size="0.82rem"), spacing="2", align_items="flex-start"), background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="18px", padding="1.1rem")), columns={"initial":"1","md":"2","lg":"3"}, spacing="3", width="100%"), rx.text("Suas malas salvas aparecem aqui.", color=MUTED))
    return wardrobe_life_shell("Mala inteligente", "Leve combinações que já funcionam.", "Monte uma lista reutilizando peças do seu armário, organizada por destino, período e ocasião.", rx.vstack(form, rx.heading("Minhas viagens", font_family=DISPLAY, color=INK, font_size="1.4rem"), plans, spacing="4", width="100%", align_items="stretch"))


def tryon_page() -> rx.Component:
    def chooser(item: dict) -> rx.Component:
        return rx.button(rx.hstack(rx.icon(rx.cond(item["selected"] == "true", "check", "plus"), size=16), rx.text(item["name"]), spacing="2"), on_click=WardrobeLifeState.toggle_tryon_item(item["local_id"]), width="100%", justify_content="flex-start", background=rx.cond(item["selected"] == "true", "rgba(233,162,59,.18)", "#FFFFFF"), color=INK, border="1px solid rgba(15,26,51,.1)", border_radius="13px", padding="0.8rem")
    board = rx.cond(WardrobeLifeState.tryon_items.length() > 0, rx.grid(rx.foreach(WardrobeLifeState.tryon_items, life_garment_card), columns={"initial":"1","sm":"2","lg":"3"}, spacing="3", width="100%"), rx.center(rx.vstack(rx.icon("layers-3", size=34, color=DENIM), rx.text("Escolha até cinco peças para montar uma composição.", color=MUTED), spacing="2", align="center"), width="100%", min_height="200px", background="#FFFFFF", border="1px dashed rgba(15,26,51,.2)", border_radius="20px"))
    return wardrobe_life_shell("Provador de combinações", "Monte seu look em um painel visual.", "O painel organiza as fotos das peças que você cadastrou. Ele não simula caimento no corpo nem gera imagens por IA.", rx.vstack(rx.callout("A prova virtual por IA depende de um provedor de imagens, consentimento explícito para fotos pessoais e configuração externa. Este painel já ajuda a visualizar as combinações do seu acervo.", icon="sparkles", color="amber", width="100%"), rx.grid(rx.foreach(WardrobeLifeState.tryon_item_cards, chooser), columns={"initial":"1","sm":"2","lg":"3"}, spacing="2", width="100%"), rx.heading("Sua composição", font_family=DISPLAY, color=INK, font_size="1.35rem"), board, spacing="4", width="100%", align_items="stretch"))


def tailoring_request_page() -> rx.Component:
    service_options = ["Ajuste de caimento", "Bainha", "Reparo", "Transformação", "Consultoria de armário"]
    request_cards = rx.cond(WardrobeLifeState.tailoring_requests.length() > 0, rx.vstack(rx.foreach(WardrobeLifeState.tailoring_requests, lambda item: rx.box(rx.hstack(rx.vstack(rx.text(item["service_type"], color=INK, font_weight="700"), rx.text(item["garment_name"], color=MUTED), spacing="1", align_items="flex-start"), rx.spacer(), rx.vstack(rx.badge(item["status"], color_scheme="amber", variant="soft"), rx.text(item["created_at"], color=MUTED, font_size="0.75rem"), spacing="1", align_items="flex-end"), width="100%"), background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="16px", padding="1rem")), spacing="2", width="100%"), rx.text("Suas solicitações aparecerão aqui após o envio.", color=MUTED))
    body = rx.vstack(rx.box(rx.vstack(rx.heading("Descreva o que sua peça precisa", font_family=DISPLAY, color=INK, font_size="1.3rem"), rx.vstack(_label("Serviço"), rx.select(service_options, value=WardrobeLifeState.tailoring_service, on_change=WardrobeLifeState.set_tailoring_service, width="100%"), spacing="1", width="100%", align_items="stretch"), field("Peça", value=WardrobeLifeState.tailoring_garment, on_change=WardrobeLifeState.set_tailoring_garment, placeholder="Ex.: calça de alfaiataria azul"), field("Data preferida (opcional)", value=WardrobeLifeState.tailoring_date, on_change=WardrobeLifeState.set_tailoring_date, type="date"), rx.text_area(value=WardrobeLifeState.tailoring_notes, on_change=WardrobeLifeState.set_tailoring_notes, placeholder="Conte o que gostaria de ajustar.", width="100%", min_height="120px"), rx.button("Enviar solicitação", on_click=WardrobeLifeState.submit_tailoring_request, background=INK, color=CHALK, border_radius="100px", font_weight="700"), rx.text("O pedido não confirma orçamento nem agendamento; a equipe precisa responder para combinar esses detalhes.", color=MUTED, font_size="0.82rem"), spacing="3", width="100%", align_items="stretch"), background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="22px", padding="1.3rem", width="100%"), rx.heading("Meus pedidos de ajuste", font_family=DISPLAY, color=INK, font_size="1.35rem"), request_cards, spacing="3", width="100%", align_items="stretch")
    return wardrobe_life_shell("Ateliê OSDROUPA", "Cuidado, reparo e novo caimento.", "Descreva a peça e o serviço que procura. O pedido fica salvo para acompanhamento.", body)


def privacy_page() -> rx.Component:
    policy = rx.vstack(
        rx.heading("Política de Privacidade", font_family=DISPLAY, color=INK, font_size=["1.7rem","2rem"]),
        rx.text("Esta página descreve o comportamento atual do projeto OSDROUPA. Antes de publicar comercialmente, o responsável pelo tratamento deve revisar o texto, identificar formalmente o controlador e confirmar prazos de retenção e canais de contato.", color=MUTED, line_height="1.7"),
        rx.heading("Quais dados podem ser tratados", font_family=DISPLAY, color=INK, font_size="1.2rem"),
        rx.text("Conta: nome, e-mail, telefone e credencial protegida por hash. O perfil também pode conter data de nascimento, pronome, estilo, tamanhos, cores favoritas e uma nota pessoal; esses campos são opcionais. Uso do produto: endereços, peças do armário, fotos enviadas ou links de imagem, looks, calendário, desafios, registros de uso e viagens. Favoritos do catálogo ficam no armazenamento local do navegador, separados pela conta selecionada. No modo SQLite, fotos enviadas ficam associadas à peça no banco local e são retornadas apenas em consultas autenticadas; no modo Xano, use links HTTPS. Comércio: endereço de entrega, itens, total, estado do pedido e referência de pagamento. Comunidade: depoimentos enviados e autorização de publicação. Privacidade: solicitações feitas por você.", color=MUTED, line_height="1.7"),
        rx.heading("Para que usamos", font_family=DISPLAY, color=INK, font_size="1.2rem"),
        rx.text("Os dados são usados para autenticar a conta, salvar seus recursos, responder a pedidos, manter segurança e operar a loja. As preferências opcionais ficam no perfil para consulta da própria pessoa; as sugestões de look usam as peças cadastradas, a ocasião escolhida e o clima. Para consultar a previsão, o servidor envia ao serviço Open-Meteo apenas a cidade e a UF do seu endereço padrão (ou da cidade que você digitar); rua, número, CEP e dados da conta não são enviados. Quando o estilista com IA está ativo, o servidor envia ao Google (API Gemini) a cidade/UF e a previsão, a ocasião, a observação opcional que você digitar e o nome, a categoria, a cor e a estação das peças disponíveis, além de produtos da loja e dos looks que você salvou recentemente (só as peças). Com a personalização ativa no perfil (padrão), também vão o estilo preferido, as cores favoritas, quais peças você mais e menos usa e suas avaliações 👍/👎 com o motivo escolhido; você pode desligar isso e apagar o histórico de avaliações no perfil a qualquer momento. As avaliações só são gravadas quando você clica nos botões. Nome, e-mail, endereço, tamanhos e fotos não são enviados. No plano gratuito da API Gemini, o Google informa que o conteúdo enviado pode ser usado para melhorar os produtos dele; por isso, evite escrever dados pessoais no campo de observação. A geração de imagens fica desativada por padrão; se a instância ativá-la e você pedir a imagem de um look, o servidor envia ao Google a descrição das peças e as fotos delas como referência, e a imagem gerada fica guardada no servidor da instância. O app não usa GPS para essa recomendação.", color=MUTED, line_height="1.7"),
        rx.heading("Compartilhamento e ambientes", font_family=DISPLAY, color=INK, font_size="1.2rem"),
        rx.text("No modo SQLite, os dados ficam no banco local configurado pelo operador da instância. No modo Xano, os dados dependem dos endpoints publicados no workspace. Se o checkout real estiver configurado, o servidor envia ao Mercado Pago os itens, valores, e-mail e referência necessários; o app não coleta nem armazena números de cartão. SMTP pode ser usado para e-mails de recuperação quando configurado. Os serviços têm seus próprios termos e avisos de privacidade.", color=MUTED, line_height="1.7"),
        rx.heading("Seus controles", font_family=DISPLAY, color=INK, font_size="1.2rem"),
        rx.text("Você pode corrigir dados do perfil, manter ou remover peças e looks, escolher se um depoimento será anônimo, revogar a autorização de publicação solicitando remoção e registrar pedidos de acesso, correção, exclusão ou informações sobre compartilhamento. Dados de pedidos podem precisar ser mantidos para obrigações legais e operacionais; cada solicitação é analisada conforme a base aplicável.", color=MUTED, line_height="1.7"),
        rx.heading("Segurança e retenção", font_family=DISPLAY, color=INK, font_size="1.2rem"),
        rx.text("Senhas são armazenadas como hash e sessões têm validade. A aplicação usa controles de propriedade por conta no backend. Em desenvolvimento, SQLite local é indicado para uma instância; o operador é responsável por proteger o arquivo, configurar backups e definir retenção. Não insira fotos íntimas ou dados que não sejam necessários.", color=MUTED, line_height="1.7"),
        rx.hstack(rx.link("Lei Geral de Proteção de Dados", href="https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm", is_external=True, color=DENIM, font_weight="700"), rx.link("Direitos dos titulares · ANPD", href="https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados/direito-dos-titulares", is_external=True, color=DENIM, font_weight="700"), flex_wrap="wrap", spacing="4"),
        spacing="3", width="100%", align_items="stretch",
    )
    request_form = rx.cond(AuthState.account_validated, rx.box(rx.vstack(rx.heading("Solicitar acesso, correção ou outra providência", font_family=DISPLAY, color=INK, font_size="1.25rem"), rx.select(["Acesso aos dados", "Correção", "Exclusão", "Portabilidade", "Informações sobre compartilhamento", "Revisão de recomendação"], value=WardrobeLifeState.privacy_request_type, on_change=WardrobeLifeState.set_privacy_request_type, width="100%"), rx.text_area(value=WardrobeLifeState.privacy_details, on_change=WardrobeLifeState.set_privacy_details, placeholder="Descreva seu pedido sem incluir dados sensíveis desnecessários.", width="100%", min_height="110px"), rx.button("Registrar solicitação", on_click=WardrobeLifeState.submit_privacy_request, background=INK, color=CHALK, border_radius="100px", font_weight="700"), rx.cond(WardrobeLifeState.privacy_requests.length() > 0, rx.vstack(rx.text("SEUS PEDIDOS", color=MUTED, font_size="0.7rem", font_weight="800", letter_spacing="0.1em"), rx.foreach(WardrobeLifeState.privacy_requests, lambda item: rx.hstack(rx.text(item["request_type"], color=INK, font_weight="600"), rx.spacer(), rx.badge(item["status"], color_scheme="gray", variant="soft"), width="100%", background="#F7F5EF", padding="0.8rem", border_radius="12px")), spacing="2", width="100%")), spacing="3", width="100%", align_items="stretch"), background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="20px", padding="1.2rem", width="100%"), rx.box(rx.text("Entre na sua conta para registrar e acompanhar uma solicitação. Você também pode consultar os canais oficiais da ANPD.", color=MUTED), rx.link("Entrar", href="/login", color=DENIM, font_weight="700"), background="#FFFFFF", border_radius="18px", padding="1.1rem"))
    return wardrobe_life_shell("Transparência", "Seus dados, explicados com clareza.", "Política informativa do ambiente OSDROUPA e canal para solicitações relacionadas aos seus dados.", rx.vstack(rx.box(policy, background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="22px", padding=["1.2rem","1.7rem"], width="100%"), request_form, spacing="4", width="100%", align_items="stretch"))


def admin_testimonials_page() -> rx.Component:
    row = lambda item: rx.box(rx.vstack(rx.hstack(rx.vstack(rx.text(item["display_name"], color=INK, font_weight="700"), rx.text("Conta #" + item["user_id"] + " · " + item["created_at"], color=MUTED, font_size="0.78rem"), spacing="1", align_items="flex-start"), rx.spacer(), rx.badge(item["status"], color_scheme="amber", variant="soft"), width="100%"), rx.text(item["body"], color=INK, line_height="1.65"), rx.cond(item["status"] == "Pendente", rx.hstack(rx.button("Publicar", on_click=WardrobeLifeState.moderate_testimonial(item["id"], "Publicado"), background=OK, color="white", border_radius="100px"), rx.button("Recusar", on_click=WardrobeLifeState.moderate_testimonial(item["id"], "Recusado"), variant="outline", color=ERROR, border_radius="100px"), spacing="3")), spacing="3", width="100%"), background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="18px", padding="1.2rem", width="100%")
    body = rx.vstack(rx.cond(WardrobeLifeState.admin_testimonials.length() > 0, rx.vstack(rx.foreach(WardrobeLifeState.admin_testimonials, row), spacing="3", width="100%"), rx.callout("Não há relatos para revisar.", icon="badge-check", color="green", width="100%")), spacing="3", width="100%", align_items="stretch")
    return rx.box(rx.el.style(CSS), management_navbar(), rx.center(rx.vstack(rx.heading("Revisão de depoimentos", font_family=DISPLAY, color=INK, font_size="2rem"), rx.text("Publique somente relatos consentidos e que descrevam experiências reais.", color=MUTED), rx.cond(WardrobeLifeState.experience_error != "", rx.callout(WardrobeLifeState.experience_error, icon="triangle-alert", color="red", width="100%")), rx.cond(WardrobeLifeState.experience_notice != "", rx.callout(WardrobeLifeState.experience_notice, icon="info", color="green", width="100%")), body, spacing="4", width="100%", max_width="1000px", padding_y="2rem", padding_x="1rem", align_items="stretch"), width="100%"), min_height="100vh", background="#F7F5EF", font_family=BODY)


def admin_tailoring_page() -> rx.Component:
    def request_card(item: dict) -> rx.Component:
        actions = rx.hstack(
            rx.button("Em análise", on_click=WardrobeLifeState.update_tailoring_request(item["id"], "Em an\u00e1lise"), variant="outline", border_radius="999px"),
            rx.button("Orçamento enviado", on_click=WardrobeLifeState.update_tailoring_request(item["id"], "Or\u00e7amento enviado"), variant="outline", border_radius="999px"),
            rx.button("Agendado", on_click=WardrobeLifeState.update_tailoring_request(item["id"], "Agendado"), variant="outline", border_radius="999px"),
            rx.button("Concluído", on_click=WardrobeLifeState.update_tailoring_request(item["id"], "Conclu\u00eddo"), background=OK, color="white", border_radius="999px"),
            rx.button("Cancelar", on_click=WardrobeLifeState.update_tailoring_request(item["id"], "Cancelado"), variant="outline", color=ERROR, border_radius="999px"),
            spacing="2", flex_wrap="wrap",
        )
        return rx.box(
            rx.vstack(
                rx.hstack(rx.vstack(rx.text(item["service_type"] + " · " + item["garment_name"], color=INK, font_weight="700"), rx.text(item["email"], color=MUTED, font_size="0.82rem"), spacing="1", align_items="flex-start"), rx.spacer(), rx.badge(item["status"], color_scheme="amber", variant="soft"), width="100%"),
                rx.text("Data preferida: " + item["preferred_date"], color=MUTED, font_size="0.82rem"),
                rx.text(item["notes"], color=MUTED, line_height="1.6"),
                actions, spacing="3", width="100%", align_items="stretch",
            ),
            background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="18px", padding="1.2rem", width="100%",
        )

    content = rx.cond(
        WardrobeLifeState.admin_tailoring_requests.length() > 0,
        rx.vstack(rx.foreach(WardrobeLifeState.admin_tailoring_requests, request_card), spacing="3", width="100%"),
        rx.callout("Não há solicitações de alfaiataria para revisar.", icon="scissors", color="green", width="100%"),
    )
    return rx.box(
        rx.el.style(CSS), management_navbar(),
        rx.center(rx.vstack(
            rx.heading("Pedidos de alfaiataria", font_family=DISPLAY, color=INK, font_size="2rem"),
            rx.text("Atualize a etapa e entre em contato com a pessoa pelo e-mail cadastrado.", color=MUTED),
            rx.cond(WardrobeLifeState.experience_error != "", rx.callout(WardrobeLifeState.experience_error, icon="triangle-alert", color="red", width="100%")),
            rx.cond(WardrobeLifeState.experience_notice != "", rx.callout(WardrobeLifeState.experience_notice, icon="info", color="green", width="100%")),
            content, spacing="4", width="100%", max_width="1000px", padding_y="2rem", padding_x="1rem", align_items="stretch",
        ), width="100%"), min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def admin_privacy_page() -> rx.Component:
    def request_card(item: dict) -> rx.Component:
        actions = rx.hstack(
            rx.button("Em análise", on_click=WardrobeLifeState.update_privacy_request(item["id"], "Em an\u00e1lise"), variant="outline", border_radius="999px"),
            rx.button("Concluída", on_click=WardrobeLifeState.update_privacy_request(item["id"], "Conclu\u00edda"), background=OK, color="white", border_radius="999px"),
            rx.button("Não aplicável", on_click=WardrobeLifeState.update_privacy_request(item["id"], "N\u00e3o aplic\u00e1vel"), variant="outline", border_radius="999px"),
            spacing="2", flex_wrap="wrap",
        )
        return rx.box(
            rx.vstack(
                rx.hstack(rx.vstack(rx.text(item["request_type"], color=INK, font_weight="700"), rx.text(item["email"], color=MUTED, font_size="0.82rem"), spacing="1", align_items="flex-start"), rx.spacer(), rx.badge(item["status"], color_scheme="amber", variant="soft"), width="100%"),
                rx.text(item["details"], color=MUTED, line_height="1.6"),
                actions,
                spacing="3", width="100%", align_items="stretch",
            ),
            background="#FFFFFF", border="1px solid rgba(15,26,51,.08)", border_radius="18px", padding="1.2rem", width="100%",
        )

    content = rx.cond(
        WardrobeLifeState.admin_privacy_requests.length() > 0,
        rx.vstack(rx.foreach(WardrobeLifeState.admin_privacy_requests, request_card), spacing="3", width="100%"),
        rx.callout("Não há solicitações de titulares para revisar.", icon="shield-check", color="green", width="100%"),
    )
    return rx.box(
        rx.el.style(CSS), management_navbar(),
        rx.center(rx.vstack(
            rx.heading("Solicitações de privacidade", font_family=DISPLAY, color=INK, font_size="2rem"),
            rx.text("Registre o andamento e responda pelo canal de atendimento vinculado à conta.", color=MUTED),
            rx.cond(WardrobeLifeState.experience_error != "", rx.callout(WardrobeLifeState.experience_error, icon="triangle-alert", color="red", width="100%")),
            rx.cond(WardrobeLifeState.experience_notice != "", rx.callout(WardrobeLifeState.experience_notice, icon="info", color="green", width="100%")),
            content, spacing="4", width="100%", max_width="1000px", padding_y="2rem", padding_x="1rem", align_items="stretch",
        ), width="100%"), min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def novelties_page() -> rx.Component:
    """Vitrine editorial para apresentar recursos j\u00e1 dispon\u00edveis no produto."""
    hero = rx.box(
        rx.grid(
            rx.vstack(
                rx.hstack(
                    rx.icon("sparkles", size=15, color=THREAD),
                    rx.text("NOVIDADES OSDROUPA", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
                    spacing="2",
                    align="center",
                    padding="0.55rem 0.85rem",
                    border="1px solid rgba(233,162,59,.3)",
                    border_radius="999px",
                    background="rgba(233,162,59,.08)",
                ),
                rx.heading(
                    "Mais inten\u00e7\u00e3o.\nMenos d\u00favida na hora de vestir.",
                    font_family=DISPLAY,
                    font_size=["2.35rem", "3.2rem", "4.15rem"],
                    line_height="1.02",
                    letter_spacing="-0.045em",
                    color=CHALK,
                    max_width="13ch",
                ),
                rx.text(
                    "Um lugar para descobrir recursos que aproximam suas roupas, seus planos e o seu jeito de se expressar.",
                    color="rgba(248,249,250,.76)",
                    font_size=["0.96rem", "1.08rem"],
                    line_height="1.75",
                    max_width="49ch",
                ),
                rx.hstack(
                    rx.link(
                        rx.button(
                            rx.hstack(rx.text("Explorar o arm\u00e1rio"), rx.icon("arrow-down", size=16), spacing="2"),
                            background=THREAD,
                            color=INK,
                            border_radius="999px",
                            font_weight="800",
                            height="48px",
                            padding_x="1.25rem",
                            _hover={"transform": "translateY(-2px)", "box_shadow": "0 12px 28px rgba(233,162,59,.22)"},
                        ),
                        href="#recursos",
                    ),
                    rx.link(
                        rx.hstack(rx.text("Conhecer os servi\u00e7os"), rx.icon("arrow-up-right", size=15), spacing="2"),
                        href="/servicos",
                        color=CHALK,
                        font_size="0.88rem",
                        font_weight="700",
                        padding="0.7rem 0.4rem",
                    ),
                    spacing="3",
                    align="center",
                    flex_wrap="wrap",
                    margin_top="0.35rem",
                ),
                spacing="5",
                align_items="flex-start",
                width="100%",
            ),
            rx.box(
                rx.box(
                    rx.box(
                        rx.hstack(rx.icon("sun", size=16, color=THREAD), rx.text("UM LOOK, V\u00c1RIAS POSSIBILIDADES", color=CHALK, font_size="0.64rem", font_weight="800", letter_spacing="0.1em"), spacing="2", align="center"),
                        rx.html(RAIL_SVG),
                        rx.hstack(
                            rx.box(rx.icon("shirt", size=15, color=INK), width="34px", height="34px", display="flex", align_items="center", justify_content="center", border_radius="12px", background=THREAD),
                            rx.vstack(rx.text("Seu acervo, em movimento", color=CHALK, font_weight="700", font_size="0.84rem"), rx.text("Pe\u00e7as, combina\u00e7\u00f5es e planos no mesmo lugar.", color="rgba(248,249,250,.63)", font_size="0.72rem"), spacing="0", align_items="flex-start"),
                            spacing="3",
                            align="center",
                            padding="0.75rem",
                            background="rgba(255,255,255,.055)",
                            border="1px solid rgba(255,255,255,.08)",
                            border_radius="16px",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    class_name="osd-editorial-orbit",
                    padding=["1rem", "1.35rem"],
                    background="linear-gradient(145deg, rgba(255,255,255,.09), rgba(255,255,255,.025))",
                    border="1px solid rgba(255,255,255,.14)",
                    border_radius="26px",
                    box_shadow="0 28px 70px rgba(0,0,0,.2)",
                    backdrop_filter="blur(12px)",
                ),
                width="100%",
                max_width="510px",
                margin_x="auto",
            ),
            columns={"initial": "1", "lg": "1.08fr 0.92fr"},
            spacing="7",
            align="center",
            width="100%",
            max_width="1180px",
            margin_x="auto",
        ),
        class_name="osd-shimmer osd-story-reveal",
        width="100%",
        padding_y=["3rem", "4.5rem", "5rem"],
        padding_x=["1rem", "2rem"],
        background="linear-gradient(125deg, #0F1A33 0%, #1F3560 58%, #263B61 100%)",
        overflow="hidden",
    )

    resources = [
        ("shirt", "SEU ACERVO", "Um arm\u00e1rio que acompanha voc\u00ea", "Cadastre e organize pe\u00e7as por categoria e estado de uso. Encontre o que j\u00e1 tem antes de pensar no pr\u00f3ximo look.", "/armario", "Organizar minhas pe\u00e7as"),
        ("sparkles", "COMBINA\u00c7\u00d5ES", "Looks com a sua assinatura", "Monte combina\u00e7\u00f5es com as pe\u00e7as do seu guarda-roupa e deixe as ideias prontas para a rotina.", "/looks", "Criar um look"),
        ("calendar-days", "PLANEJAMENTO", "Vista os seus planos", "Distribua combina\u00e7\u00f5es na agenda e tenha uma vis\u00e3o mais clara do que pretende vestir.", "/calendario", "Abrir a agenda"),
        ("scissors", "ALFAIATARIA", "Ajustes pensados para voc\u00ea", "Explore servi\u00e7os de alfaiataria e conhe\u00e7a o cuidado por tr\u00e1s de uma pe\u00e7a feita para vestir bem.", "/servicos", "Conhecer servi\u00e7os"),
        ("lightbulb", "INSPIRA\u00c7\u00c3O", "Ideias que saem do papel", "Leia o caderno editorial, descubra refer\u00eancias e leve pequenas ideias para o seu dia a dia.", "/inspiracao", "Buscar inspira\u00e7\u00e3o"),
        ("leaf", "NOVOS H\u00c1BITOS", "Desafios no seu ritmo", "Experimente pr\u00e1ticas de uso consciente e acompanhe seu progresso em desafios pessoais.", "/desafios", "Ver desafios"),
    ]
    feature_cards = [
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.center(rx.icon(icon, size=19, color=THREAD), width="46px", height="46px", border_radius="15px", background="rgba(233,162,59,.12)"),
                    rx.spacer(),
                    rx.badge("NO PRODUTO", color_scheme="green", variant="soft", border_radius="999px"),
                    width="100%",
                    align="center",
                ),
                rx.text(label, color=MUTED, font_size="0.65rem", font_weight="800", letter_spacing="0.13em"),
                rx.heading(title, font_family=DISPLAY, color=INK, font_size=["1.18rem", "1.34rem"], line_height="1.1"),
                rx.text(description, color=MUTED, font_size="0.88rem", line_height="1.7", min_height=["auto", "5.1rem"]),
                rx.link(
                    rx.hstack(rx.text(action), rx.icon("arrow-up-right", size=15), spacing="2"),
                    href=href,
                    color=DENIM,
                    font_size="0.84rem",
                    font_weight="800",
                    margin_top="auto",
                    _hover={"color": THREAD},
                ),
                spacing="3",
                align_items="flex-start",
                width="100%",
                height="100%",
            ),
            class_name="osd-motion-card osd-story-reveal",
            background="#FFFFFF",
            border="1px solid rgba(15,26,51,.08)",
            border_radius="24px",
            padding=["1.2rem", "1.45rem"],
            min_height="290px",
            width="100%",
        )
        for icon, label, title, description, href, action in resources
    ]

    collection = rx.box(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text("UM ECOSSISTEMA QUE SE CONECTA", color=THREAD, font_size="0.68rem", font_weight="800", letter_spacing="0.14em"),
                    rx.heading("Novas formas de usar o que voc\u00ea j\u00e1 ama.", font_family=DISPLAY, color=INK, font_size=["1.85rem", "2.6rem"], line_height="1.06", letter_spacing="-0.035em", max_width="18ch"),
                    spacing="3",
                    align_items="flex-start",
                ),
                rx.spacer(),
                rx.text("Cada \u00e1rea tem uma fun\u00e7\u00e3o pr\u00f3pria; juntas, formam uma experi\u00eancia mais organizada e pessoal.", color=MUTED, font_size="0.92rem", line_height="1.7", max_width="40ch", display=["none", "block"]),
                width="100%",
                align="end",
                flex_wrap="wrap",
                spacing="4",
            ),
            rx.grid(
                *feature_cards,
                columns={"initial": "1", "sm": "2", "xl": "3"},
                spacing="4",
                width="100%",
                id="recursos",
            ),
            spacing="6",
            width="100%",
            max_width="1180px",
            margin_x="auto",
        ),
        class_name="osd-story-reveal",
        padding_y=["3rem", "4.5rem"],
        padding_x=["1rem", "2rem"],
        width="100%",
        background="linear-gradient(180deg, #F8F9FA 0%, #F3F1EA 100%)",
    )

    next_step = rx.box(
        rx.hstack(
            rx.vstack(
                rx.text("O PR\u00d3XIMO PASSO COME\u00c7A NO SEU ESPA\u00c7O", color=THREAD, font_size="0.67rem", font_weight="800", letter_spacing="0.13em"),
                rx.heading("Seu estilo n\u00e3o precisa caber em uma s\u00f3 ideia.", font_family=DISPLAY, color=CHALK, font_size=["1.65rem", "2.25rem"], line_height="1.08", max_width="22ch"),
                rx.text("Comece pelo arm\u00e1rio, salve uma combina\u00e7\u00e3o ou explore um servi\u00e7o. Voc\u00ea escolhe por onde seguir.", color="rgba(248,249,250,.72)", font_size="0.91rem", line_height="1.7", max_width="52ch"),
                spacing="3",
                align_items="flex-start",
            ),
            rx.spacer(),
            rx.link(
                rx.button(rx.hstack(rx.text("Entrar no meu espa\u00e7o"), rx.icon("arrow-up-right", size=16), spacing="2"), background=THREAD, color=INK, border_radius="999px", font_weight="800", height="48px", padding_x="1.2rem"),
                href="/armario",
                flex_shrink="0",
            ),
            spacing="6",
            align="center",
            flex_wrap="wrap",
            width="100%",
            max_width="1180px",
            margin_x="auto",
        ),
        class_name="osd-story-reveal",
        background=f"linear-gradient(125deg, {INK}, {DENIM})",
        padding_y=["2.2rem", "3rem"],
        padding_x=["1.2rem", "2.2rem"],
        border_radius=["22px", "30px"],
        width="calc(100% - 2rem)",
        max_width="1180px",
        margin_y=["1rem", "2rem"],
        margin_x="auto",
        border="1px solid rgba(233,162,59,.2)",
        box_shadow="0 24px 60px rgba(15,26,51,.12)",
    )
    return marketing_page_shell(hero, collection, next_step)


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
                    rx.link("Como funciona", href="/como-funciona", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Serviços", href="/servicos", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Novidades", href="/novidades", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Depoimentos", href="/depoimentos", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Privacidade", href="/privacidade", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Loja", href="/loja", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    rx.link("Entrar", href="/login", color=MUTED, _hover={"color": CHALK}, font_size="0.88rem"),
                    spacing="4", flex_wrap="wrap",
                    width="100%",
                ),
                width="100%",
                align_items="center",
                wrap="wrap",
            ),
            rx.divider(color_scheme="gray", opacity=0.15, margin_y="1.5rem"),
            rx.hstack(
                rx.text(
                    "© 2026 OsDRoupa. Todos os direitos reservados.",
                    color=MUTED,
                    font_size="0.8rem",
                ),
                rx.spacer(),
                rx.text(f"Feito com Reflex + {BACKEND_LABEL} no Brasil 🇧🇷", color=MUTED, font_size="0.8rem"),
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
        marketing_scroll_progress(),
        rx.cond(
            AuthState.session_error != "",
            rx.center(
                rx.vstack(
                    rx.callout(AuthState.session_error, icon="cloud-alert", color="amber", width="100%"),
                    rx.button("Validar sessão novamente", on_click=AuthState.restore_session, variant="outline", color=CHALK),
                    width="100%",
                    max_width="1220px",
                    padding_x=["1rem", "1.5rem", "2rem"],
                    padding_y="0.8rem",
                    align_items="stretch",
                ),
                width="100%",
            ),
        ),
        home_hero_section(),
        home_scroll_cue(),
        home_marquee_strip(),
        home_features_section(),
        home_osm_definition_block(),
        home_how_section(),
        home_services_teaser(),
        home_numbers_banner(),
        home_testimonials_teaser(),
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
        site_navbar(),
        rx.center(
            rx.box(
                brand_panel(),
                form_panel(),
                display="grid",
                grid_template_columns=["1fr", "1fr", "1.15fr 0.85fr"],
                width="100%",
                max_width="1180px",
                border_radius="28px",
                overflow="hidden",
                box_shadow="0 35px 90px rgba(0,0,0,0.28)",
                background=INK,
            ),
            width="100%",
            min_height="calc(100vh - 120px)",
            padding=["1rem", "1.5rem", "2rem"],
        ),
        width="100%",
        min_height="100vh",
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


def reset_password_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS),
        site_navbar(),
        rx.center(
            rx.box(
                rx.vstack(
                    rx.link(rx.hstack(rx.html(LOGO_SVG), rx.text("OSDROUPA", font_family=DISPLAY, color=INK, font_weight="800"), spacing="2", align="center"), href="/"),
                    rx.text("SEGURANÇA DA CONTA", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"),
                    rx.heading("Crie uma nova senha", font_family=DISPLAY, color=INK, font_size="2rem"),
                    rx.text("Use a senha recebida no link de recuperação. O link expira após 30 minutos.", color=MUTED, line_height="1.6"),
                    password_field("Nova senha", "Mínimo de 8 caracteres", AuthState.reset_password, AuthState.set_reset_password),
                    password_field("Confirmar senha", "Repita a nova senha", AuthState.reset_confirmation, AuthState.set_reset_confirmation),
                    rx.cond(AuthState.reset_message != "", rx.callout(AuthState.reset_message, icon=rx.cond(AuthState.reset_error, "triangle_alert", "circle_check"), color=rx.cond(AuthState.reset_error, "red", "green"), width="100%")),
                    rx.button("Atualizar senha", on_click=AuthState.submit_password_reset, width="100%", background=INK, color=CHALK, border_radius="100px", font_weight="700"),
                    rx.link("Voltar ao login", href="/login", color=DENIM, font_weight="700"),
                    spacing="4", width="100%", align_items="stretch",
                ),
                width="100%", max_width="480px", padding=["1.4rem", "2rem"], background="#FFFFFF", border_radius="24px", box_shadow="0 18px 50px rgba(15,26,51,0.12)",
            ),
            min_height="100vh", padding="1rem", background="#F7F5EF",
        ),
    )


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
        rx.cond(
            AuthState.account_validated,
            _enderecos_content(),
            auth_loading_screen(AddressState.load_addresses),
        ),
        min_height="100vh",
    )


def _enderecos_content() -> rx.Component:
    """Página de gerenciamento de endereços do cliente (Change 003)."""
    return rx.box(
        rx.el.style(CSS),
        store_navbar(),

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
    """A ?rea pessoal usa o mesmo cabe?alho responsivo do restante do produto."""
    return site_navbar()

def auth_loading_screen(retry_event=AuthState.restore_session) -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.cond(
                AuthState.session_error != "",
                rx.vstack(
                    rx.icon("cloud-alert", size=30, color=ERROR),
                    rx.text(AuthState.session_error, color=INK, text_align="center", max_width="28rem"),
                    rx.button("Tentar novamente", on_click=retry_event, variant="outline", color=DENIM),
                    rx.link("Voltar ao início", href="/", color=DENIM, font_weight="600"),
                    spacing="3",
                    align="center",
                ),
                rx.vstack(
                    rx.spinner(size="3", color=THREAD),
                    rx.text("Validando sua conta…", color=MUTED, font_weight="600"),
                    spacing="3",
                    align="center",
                ),
            ),
            width="100%",
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


def profile_edit_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("EDITAR CONTA", color=THREAD, font_size="0.68rem", font_weight="800", letter_spacing="0.14em"),
            rx.heading("Um perfil que combina com você", font_family=DISPLAY, font_size="1.5rem", color=INK),
            rx.text("Atualize seus dados e personalize as recomendações. As preferências de estilo e tamanho são opcionais.", color=MUTED, line_height="1.6"),
            rx.grid(
                field("Nome completo", value=AuthState.profile_name_draft, on_change=AuthState.set_profile_name_draft, placeholder="Seu nome"),
                field("Celular", value=AuthState.profile_phone_draft, on_change=AuthState.set_profile_phone_draft, placeholder="(11) 99999-9999", type="tel"),
                field("Data de nascimento · opcional", value=AuthState.profile_birth_date_draft, on_change=AuthState.set_profile_birth_date_draft, type="date"),
                rx.vstack(
                    _label("Pronome · opcional"),
                    rx.select(
                        ["Prefiro não informar", "Ela/dela", "Ele/dele", "Elu/delu"],
                        value=AuthState.profile_pronouns_draft,
                        on_change=AuthState.set_profile_pronouns_draft,
                        width="100%",
                    ),
                    spacing="1", width="100%", align_items="stretch",
                ),
                columns={"initial": "1", "sm": "2"}, spacing="3", width="100%",
            ),
            rx.divider(),
            rx.text("PREFERÊNCIAS DE ESTILO", color=THREAD, font_size="0.68rem", font_weight="800", letter_spacing="0.14em"),
            rx.grid(
                rx.vstack(
                    _label("Estilo que mais combina com você"),
                    rx.select(
                        ["Prefiro não definir", "Casual", "Clássico", "Minimalista", "Criativo", "Streetwear", "Romântico", "Esportivo"],
                        value=AuthState.profile_style_draft,
                        on_change=AuthState.set_profile_style_draft,
                        width="100%",
                    ),
                    spacing="1", width="100%", align_items="stretch",
                ),
                field("Cores que você gosta", value=AuthState.profile_colors_draft, on_change=AuthState.set_profile_colors_draft, placeholder="Ex.: azul, verde e tons neutros"),
                columns={"initial": "1", "sm": "2"}, spacing="3", width="100%",
            ),
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.switch(checked=AuthState.profile_ai_personalization_draft, on_change=AuthState.set_profile_ai_personalization_draft),
                        rx.text("Personalizar o estilista com IA", color=INK, font_weight="700", font_size="0.9rem"),
                        spacing="2", align="center",
                    ),
                    rx.text("Quando ativo, o estilista usa seu estilo, suas cores favoritas, as peças que você mais e menos usa e suas avaliações 👍/👎 dos looks. Desligado, ele usa só o clima, a ocasião e as peças disponíveis, e os botões de avaliação somem. Tamanhos não são enviados. Salve o perfil para aplicar.", color=MUTED, font_size="0.82rem", line_height="1.6"),
                    rx.button("Apagar meu histórico de avaliações", on_click=AuthState.clear_ai_feedback, variant="ghost", color_scheme="red", size="1"),
                    spacing="2", width="100%", align_items="start",
                ),
                background="#F7F5EF", border_radius="16px", padding="0.85rem", width="100%",
            ),
            rx.text("Tamanhos · opcionais", color=INK, font_weight="700", font_size="0.9rem"),
            rx.grid(
                field("Parte de cima", value=AuthState.profile_top_size_draft, on_change=AuthState.set_profile_top_size_draft, placeholder="Ex.: M"),
                field("Parte de baixo", value=AuthState.profile_bottom_size_draft, on_change=AuthState.set_profile_bottom_size_draft, placeholder="Ex.: 40"),
                field("Calçado", value=AuthState.profile_shoe_size_draft, on_change=AuthState.set_profile_shoe_size_draft, placeholder="Ex.: 37"),
                columns={"initial": "1", "sm": "3"}, spacing="3", width="100%",
            ),
            rx.vstack(
                _label("Uma nota sobre seu estilo · opcional"),
                rx.text_area(
                    value=AuthState.profile_bio_draft,
                    on_change=AuthState.set_profile_bio_draft,
                    placeholder="Conte o que você gosta de vestir ou o que procura nas suas combinações.",
                    max_length=240,
                    min_height="100px",
                    width="100%",
                    background="#FFFFFF",
                    border="1px solid rgba(15,26,51,0.12)",
                    border_radius="14px",
                    padding="0.85rem",
                ),
                spacing="1", width="100%", align_items="stretch",
            ),
            rx.callout("Seu e-mail é usado para entrar e não pode ser alterado por este formulário. As informações de tamanho são opcionais e podem ser apagadas quando quiser.", icon="shield-check", color="blue", width="100%"),
            rx.cond(
                AuthState.profile_save_message != "",
                rx.text(AuthState.profile_save_message, color=rx.cond(AuthState.profile_save_error, ERROR, OK), font_size="0.84rem"),
            ),
            rx.hstack(
                rx.button("Salvar meu perfil", on_click=AuthState.save_profile, background=INK, color=CHALK, border_radius="100px", font_weight="700"),
                rx.link("Gerenciar endereços", href="/enderecos", color=DENIM, font_weight="700"),
                spacing="4", align="center", flex_wrap="wrap",
            ),
            spacing="4", align_items="stretch", width="100%",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.07)", border_radius="24px", padding=["1.4rem", "2rem"],
        box_shadow="0 16px 42px rgba(15,26,51,0.06)",
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
                rx.text("Sessão ativa e validada", font_size="0.82rem", color=OK, font_weight="600"),
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
                profile_edit_card(),
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
        rx.cond(
            AuthState.account_validated,
            content,
            auth_loading_screen(AuthState.require_authenticated),
        ),
        min_height="100vh",
        background="#F7F5EF",
        font_family=BODY,
    )


def wardrobe_item_card(item: dict) -> rx.Component:
    garment_art = rx.hstack(
        rx.center(
            rx.cond(
                item["image_url"] != "",
                rx.image(
                    src=item["image_url"],
                    alt="Foto de " + item["name"],
                    width="100%",
                    height="150px",
                    object_fit="cover",
                    border_radius="17px",
                ),
                rx.icon("shirt", size=46, color=DENIM),
            ),
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
                width="100%",
                align="center",
            ),
            rx.heading(item["name"], font_family=DISPLAY, font_size="1.12rem", color=INK),
            rx.cond(
                (item["color"] != "") | (item["brand"] != "") | (item["size"] != ""),
                rx.text(
                    rx.cond(item["color"] != "", item["color"], ""),
                    rx.cond((item["color"] != "") & (item["brand"] != ""), " · ", ""),
                    rx.cond(item["brand"] != "", item["brand"], ""),
                    rx.cond((item["size"] != "") & ((item["color"] != "") | (item["brand"] != "")), " · ", ""),
                    rx.cond(item["size"] != "", "Tam. " + item["size"], ""),
                    color=MUTED,
                    font_size="0.78rem",
                ),
            ),
            rx.select(
                WARDROBE_STATUSES,
                value=item["status"],
                on_change=WardrobeState.update_item_status(item["id"]),
                size="1",
                width="100%",
                aria_label="Estado de uso da peça",
            ),
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
            rx.grid(
                rx.vstack(
                    rx.text("Estado de uso", font_size="0.82rem", font_weight="700", color=INK),
                    rx.select(WARDROBE_STATUSES, value=WardrobeState.new_item_status, on_change=WardrobeState.set_new_item_status, width="100%"),
                    align_items="stretch",
                    width="100%",
                    spacing="1",
                ),
                field("Cor", placeholder="Ex.: Azul-marinho", value=WardrobeState.new_item_color, on_change=WardrobeState.set_new_item_color),
                field("Estação", placeholder="Ex.: Todas as estações", value=WardrobeState.new_item_season, on_change=WardrobeState.set_new_item_season),
                field("Tamanho", placeholder="Ex.: M", value=WardrobeState.new_item_size, on_change=WardrobeState.set_new_item_size),
                field("Marca", placeholder="Opcional", value=WardrobeState.new_item_brand, on_change=WardrobeState.set_new_item_brand),
                columns={"initial": "1", "sm": "2"},
                spacing="3",
                width="100%",
            ),
            field("Valor que você pagou (opcional)", placeholder="Ex.: 129,90", value=WardrobeState.new_item_purchase_price, on_change=WardrobeState.set_new_item_purchase_price, type="text"),
            rx.vstack(
                rx.text("Foto da peça", font_size="0.82rem", font_weight="700", color=INK),
                rx.upload(
                    rx.vstack(
                        rx.icon("image", size=25, color=DENIM),
                        rx.text("Arraste uma foto ou toque para escolher", color=INK, font_weight="600", text_align="center"),
                        rx.text("JPG, PNG ou WebP · até 2 MB", color=MUTED, font_size="0.76rem"),
                        align="center",
                        spacing="1",
                        width="100%",
                    ),
                    id=WARDROBE_IMAGE_UPLOAD_ID,
                    accept={"image/jpeg": [".jpg", ".jpeg"], "image/png": [".png"], "image/webp": [".webp"]},
                    max_files=1,
                    max_size=MAX_WARDROBE_IMAGE_BYTES,
                    multiple=False,
                    width="100%",
                    padding="1.1rem",
                    border="1px dashed #AEB9C9",
                    border_radius="16px",
                    background="#F8FAFC",
                    cursor="pointer",
                ),
                rx.foreach(
                    rx.selected_files(WARDROBE_IMAGE_UPLOAD_ID),
                    lambda filename: rx.text(filename, color=MUTED, font_size="0.76rem"),
                ),
                rx.button(
                    rx.icon("upload", size=16),
                    "Usar foto selecionada",
                    on_click=WardrobeState.upload_new_item_image(rx.upload_files(upload_id=WARDROBE_IMAGE_UPLOAD_ID)),
                    variant="outline",
                    color=DENIM,
                    border_radius="100px",
                    size="2",
                    type="button",
                ),
                rx.cond(
                    WardrobeState.new_item_image_data_uri != "",
                    rx.hstack(
                        rx.image(
                            src=WardrobeState.new_item_image_data_uri,
                            alt="Prévia da foto da peça",
                            width="96px",
                            height="112px",
                            object_fit="cover",
                            border_radius="12px",
                        ),
                        rx.text("Foto pronta para salvar no seu armário.", color=MUTED, font_size="0.8rem"),
                        align="center",
                        spacing="3",
                        width="100%",
                    ),
                ),
                field(
                    "Ou cole o link direto da imagem",
                    placeholder="https://loja.com/imagens/minha-peca.jpg",
                    value=WardrobeState.new_item_image_url,
                    on_change=WardrobeState.set_new_item_image_url,
                    type="url",
                ),
                rx.text(
                    "Use o endereço HTTPS do arquivo da imagem (JPG, PNG ou WebP), não o link da página do produto. Alguns sites bloqueiam a exibição de imagens externas.",
                    color=MUTED,
                    font_size="0.76rem",
                    line_height="1.5",
                ),
                rx.cond(
                    (WardrobeState.new_item_image_url != "") & (WardrobeState.new_item_image_data_uri == ""),
                    rx.image(
                        src=WardrobeState.new_item_image_url,
                        alt="Prévia da imagem externa",
                        width="96px",
                        height="112px",
                        object_fit="cover",
                        border_radius="12px",
                    ),
                ),
                spacing="2",
                align_items="stretch",
                width="100%",
            ),
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
                rx.grid(
                    rx.link(
                        rx.hstack(rx.icon("sparkles", size=19, color=DENIM), rx.vstack(rx.text("Montar um look", color=INK, font_weight="700"), rx.text("Combine peças que já tem", color=MUTED, font_size="0.77rem"), spacing="0", align_items="flex-start"), spacing="3", align="center"),
                        href="/looks", background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="16px", padding="1rem", width="100%",
                        _hover={"border_color": THREAD, "transform": "translateY(-2px)"}, transition="transform 180ms ease, border-color 180ms ease",
                    ),
                    rx.link(
                        rx.hstack(rx.icon("calendar-days", size=19, color=DENIM), rx.vstack(rx.text("Planejar a semana", color=INK, font_weight="700"), rx.text("Veja seus looks por data", color=MUTED, font_size="0.77rem"), spacing="0", align_items="flex-start"), spacing="3", align="center"),
                        href="/calendario", background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="16px", padding="1rem", width="100%",
                        _hover={"border_color": THREAD, "transform": "translateY(-2px)"}, transition="transform 180ms ease, border-color 180ms ease",
                    ),
                    columns={"initial": "1", "sm": "2"},
                    spacing="3",
                    width="100%",
                ),
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
                rx.text("As peças sincronizadas ficam na sua conta; sem conexão, o armário mantém a cópia local deste navegador.", color=MUTED, font_size="0.78rem", text_align="center", width="100%"),
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
        rx.cond(
            AuthState.account_validated,
            content,
            auth_loading_screen(WardrobeState.load_wardrobe),
        ),
        min_height="100vh",
        background="#F7F5EF",
        font_family=BODY,
    )


def look_garment_picker(item: dict) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=item["selected"] == "true",
            on_change=LookState.toggle_garment(item["local_id"]),
            color_scheme="amber",
            aria_label="Incluir " + item["name"] + " no look",
        ),
        rx.vstack(
            rx.text(item["name"], color=INK, font_weight="700", font_size="0.88rem"),
            rx.text(item["category"] + " · " + item["status"], color=MUTED, font_size="0.76rem"),
            spacing="0",
            align_items="flex-start",
        ),
        width="100%",
        align="center",
        padding="0.8rem",
        background=rx.cond(item["selected"] == "true", "rgba(233,162,59,0.12)", "#FFFFFF"),
        border="1px solid rgba(15,26,51,0.08)",
        border_radius="14px",
        transition="background 180ms ease, border-color 180ms ease",
    )


def look_card(look: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.badge(look["occasion"], color_scheme="amber", variant="soft"),
                rx.spacer(),
                rx.text(rx.cond(look["date"] != "", look["date"], "Sem data"), color=MUTED, font_size="0.78rem"),
                width="100%",
                align="center",
            ),
            rx.heading(look["name"], font_family=DISPLAY, color=INK, font_size="1.2rem"),
            rx.text(look["garment_names"], color=MUTED, font_size="0.84rem", line_height="1.5"),
            rx.hstack(
                rx.text(look["garment_count"] + " peças", color=DENIM, font_size="0.78rem", font_weight="700"),
                rx.spacer(),
                rx.button(
                    rx.icon("sparkles", size=14), "Avaliar com IA",
                    on_click=LookState.evaluate_look(look["id"]),
                    loading=LookState.review_loading & (LookState.review_look_id == look["id"]),
                    variant="soft", size="1", border_radius="100px",
                ),
                rx.button(
                    rx.icon("trash-2", size=15),
                    on_click=LookState.delete_look(look["id"]),
                    variant="ghost",
                    color=MUTED,
                    aria_label="Remover look",
                    _hover={"color": ERROR, "background": "rgba(180,55,47,0.08)"},
                ),
                width="100%",
                align="center",
            ),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
        background="#FFFFFF",
        border="1px solid rgba(15,26,51,0.08)",
        border_radius="20px",
        padding="1.15rem",
        width="100%",
        transition="transform 180ms ease, box-shadow 180ms ease",
        _hover={"transform": "translateY(-2px)", "box_shadow": "0 12px 30px rgba(15,26,51,0.08)"},
    )


def manual_swap_row(swap: LookSwap) -> rx.Component:
    selectable = swap.aplicavel & (swap.entra.origem == "armario")
    return rx.hstack(
        rx.cond(
            selectable,
            rx.checkbox(checked=LookState.review_selected_swaps.contains(swap.id), on_change=lambda _checked: LookState.toggle_review_swap(swap.id)),
            rx.icon("lightbulb", size=16, color=THREAD),
        ),
        swap_description(swap),
        rx.cond(swap.entra.origem == "catalogo", rx.link("Ver na loja", href=f"/produto?id={swap.entra.ref}", color=DENIM, font_size="0.78rem", font_weight="700", white_space="nowrap")),
        spacing="3", align="start", width="100%",
    )


def manual_review_panel() -> rx.Component:
    review = LookState.look_review
    return rx.cond(
        LookState.review_look_id != "",
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.hstack(rx.icon("sparkles", size=18, color=THREAD), rx.heading("Avaliação: ", LookState.review_look_name, font_family=DISPLAY, color=INK, font_size="1.1rem"), spacing="2", align="center"),
                    rx.spacer(),
                    rx.button(rx.icon("x", size=15), on_click=LookState.close_review, variant="ghost", color=MUTED, aria_label="Fechar avaliação"),
                    width="100%", align="center",
                ),
                rx.cond(LookState.review_loading, rx.hstack(rx.spinner(), rx.text("Avaliando o look com o clima de agora...", color=MUTED), spacing="2", align="center")),
                rx.cond(LookState.review_error != "", rx.callout(LookState.review_error, icon="triangle-alert", color="red", width="100%")),
                rx.cond(
                    review.disponivel,
                    rx.vstack(
                        review_summary(review),
                        rx.cond(
                            review.trocas.length() > 0,
                            rx.vstack(
                                rx.text("Trocas sugeridas", color=INK, font_weight="700", font_size="0.9rem"),
                                rx.foreach(review.trocas, manual_swap_row),
                                rx.button("Salvar versão ajustada", on_click=LookState.save_adjusted_look, background=THREAD, color=INK, border_radius="100px", font_weight="700", size="2"),
                                rx.text("A versão ajustada é salva como um novo look; o original continua na lista.", color=MUTED, font_size="0.76rem"),
                                spacing="2", width="100%", align_items="stretch",
                            ),
                        ),
                        spacing="3", width="100%", align_items="stretch",
                    ),
                ),
                spacing="3", width="100%", align_items="stretch",
            ),
            background="#FFFFFF", border="1px solid rgba(233,162,59,0.45)", border_radius="20px", padding="1.15rem", width="100%",
        ),
    )


def looks_page() -> rx.Component:
    composer = rx.box(
        rx.vstack(
            rx.heading("Monte um look", font_family=DISPLAY, color=INK, font_size="1.35rem"),
            rx.text("Escolha peças do seu armário e, se quiser, marque o dia em que pretende usar.", color=MUTED, font_size="0.88rem", line_height="1.5"),
            field("Nome do look", placeholder="Ex.: Reunião de quinta", value=LookState.look_name, on_change=LookState.set_look_name),
            rx.grid(
                rx.vstack(
                    rx.text("Ocasião", font_size="0.82rem", font_weight="700", color=INK),
                    rx.select(LOOK_OCCASIONS, value=LookState.look_occasion, on_change=LookState.set_look_occasion, width="100%"),
                    spacing="1", align_items="stretch", width="100%",
                ),
                rx.vstack(
                    rx.text("Planejar para", font_size="0.82rem", font_weight="700", color=INK),
                    rx.input(type="date", value=LookState.look_date, on_change=LookState.set_look_date, **INPUT_STYLE),
                    spacing="1", align_items="stretch", width="100%",
                ),
                columns={"initial": "1", "sm": "2"},
                spacing="3",
                width="100%",
            ),
            rx.hstack(
                rx.text("Peças", color=INK, font_weight="700"),
                rx.spacer(),
                rx.text(LookState.selected_garment_keys.length().to_string() + " selecionadas", color=MUTED, font_size="0.78rem"),
                width="100%",
            ),
            rx.cond(
                LookState.wardrobe_items.length() == 0,
                rx.callout("Adicione peças ao armário para montar seu primeiro look.", icon="shirt", color="amber", width="100%"),
                rx.vstack(rx.foreach(LookState.garment_picker, look_garment_picker), spacing="2", width="100%", max_height="300px", overflow_y="auto"),
            ),
            rx.cond(LookState.look_error != "", rx.text(LookState.look_error, color=ERROR, font_size="0.82rem", role="alert")),
            rx.button("Salvar look", on_click=LookState.save_look, background=THREAD, color=INK, font_weight="700", border_radius="100px", width="100%"),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
        background="#FFFFFF",
        border="1px solid rgba(15,26,51,0.08)",
        border_radius="22px",
        padding=["1.1rem", "1.5rem"],
        width="100%",
        height="fit-content",
    )
    saved_looks = rx.vstack(
        rx.hstack(
            rx.vstack(rx.heading("Seus looks", font_family=DISPLAY, color=INK, font_size="1.45rem"), rx.text("Combinações para repetir e planejar.", color=MUTED, font_size="0.84rem"), spacing="1", align_items="flex-start"),
            rx.spacer(),
            rx.link("Abrir calendário", href="/calendario", color=DENIM, font_weight="700", font_size="0.85rem"),
            width="100%", align="center", wrap="wrap",
        ),
        manual_review_panel(),
        rx.cond(
            LookState.look_cards.length() == 0,
            rx.center(rx.vstack(rx.icon("sparkles", size=34, color=THREAD), rx.text("Seu primeiro look começa com uma peça favorita.", color=INK, text_align="center", font_weight="600"), spacing="3", align="center"), background="#FFFFFF", border="1px dashed rgba(31,53,96,0.24)", border_radius="20px", padding="2rem", width="100%"),
            rx.grid(rx.foreach(LookState.look_cards, look_card), columns={"initial": "1", "md": "2"}, spacing="3", width="100%"),
        ),
        spacing="4",
        align_items="stretch",
        width="100%",
    )
    content = rx.box(
        workspace_navbar(),
        rx.center(
            rx.vstack(
                rx.hstack(rx.vstack(rx.text("ESTILO EM MOVIMENTO", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"), rx.heading("Looks que contam a sua história.", font_family=DISPLAY, color=INK, font_size=["2.1rem", "3.2rem"], line_height="1.08"), rx.text("Reaproveite suas peças e deixe combinações prontas para os próximos dias.", color=MUTED, font_size="0.95rem"), spacing="2", align_items="flex-start"), rx.spacer(), rx.link("Meu armário", href="/armario", color=DENIM, font_weight="700"), width="100%", align="center", wrap="wrap"),
                rx.callout(LookState.look_notice, icon="cloud-check", color=rx.cond(LookState.looks_remote_ready, "green", "amber"), width="100%"),
                rx.grid(composer, saved_looks, columns={"initial": "1", "lg": "0.9fr 1.1fr"}, spacing="5", width="100%", align_items="start"),
                width="100%", max_width="1200px", spacing="5", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
            ),
            width="100%",
        ),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )
    return rx.box(
        rx.el.style(CSS),
        rx.cond(
            AuthState.account_validated,
            content,
            auth_loading_screen(LookState.load_looks),
        ),
        min_height="100vh",
        background="#F7F5EF",
        font_family=BODY,
    )


def calendar_page() -> rx.Component:
    content = rx.box(
        workspace_navbar(),
        rx.center(
            rx.vstack(
                rx.hstack(
                    rx.vstack(rx.text("PLANEJAMENTO PESSOAL", color=THREAD, font_size="0.7rem", font_weight="800", letter_spacing="0.14em"), rx.heading("Seu calendário de looks.", font_family=DISPLAY, color=INK, font_size=["2.1rem", "3.2rem"]), rx.text("Deixe as combinações prontas para os dias que importam.", color=MUTED), spacing="2", align_items="flex-start"),
                    rx.spacer(),
                    rx.link("Montar um look", href="/looks", background=INK, color=CHALK, padding="0.8rem 1.2rem", border_radius="100px", font_weight="700"),
                    width="100%", align="center", wrap="wrap",
                ),
                rx.callout(LookState.look_notice, icon="cloud-check", color=rx.cond(LookState.looks_remote_ready, "green", "amber"), width="100%"),
                rx.cond(
                    LookState.planned_look_cards.length() == 0,
                    rx.center(rx.vstack(rx.icon("calendar-days", size=38, color=DENIM), rx.heading("Sua agenda está livre.", font_family=DISPLAY, color=INK), rx.text("Monte um look e escolha uma data para vê-lo aqui.", color=MUTED, text_align="center"), rx.link("Planejar primeiro look", href="/looks", color=DENIM, font_weight="700"), spacing="3", align="center"), background="#FFFFFF", border="1px dashed rgba(31,53,96,0.24)", border_radius="22px", padding=["2rem", "3rem"], width="100%", min_height="300px"),
                    rx.vstack(rx.foreach(LookState.planned_look_cards, look_card), spacing="3", width="100%"),
                ),
                width="100%", max_width="1000px", spacing="5", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
            ),
            width="100%",
        ),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )
    return rx.box(
        rx.el.style(CSS),
        rx.cond(
            AuthState.account_validated,
            content,
            auth_loading_screen(LookState.load_looks),
        ),
        min_height="100vh",
        background="#F7F5EF",
        font_family=BODY,
    )


def store_navbar() -> rx.Component:
    """Compatibilidade com as p?ginas de loja; usa a navega??o compartilhada."""
    return site_navbar()

def store_product_card(product: dict) -> rx.Component:
    image_panel = rx.box(
        rx.cond(
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
        ),
        rx.button(
            rx.cond(product["favorite"] == "true", rx.icon("heart", size=18, fill="currentColor"), rx.icon("heart", size=18)),
            on_click=StoreState.toggle_favorite(product["id"]),
            aria_label=rx.cond(product["favorite"] == "true", "Remover dos favoritos", "Salvar nos favoritos"),
            title=rx.cond(product["favorite"] == "true", "Remover dos favoritos", "Salvar nos favoritos"),
            position="absolute", top="10px", right="10px", width="42px", height="42px",
            display="flex", align_items="center", justify_content="center",
            border_radius="50%", background="#FFFFFF", color=ERROR,
            box_shadow="0 8px 22px rgba(15,26,51,0.15)",
            _hover={"transform": "scale(1.07)", "background": "#FFF5F4"},
        ),
        position="relative", width="100%",
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
                rx.badge(product["product_type"], color_scheme="blue", variant="soft"),
                rx.cond(product["demonstration"] == "true", rx.badge("Produto demonstrativo", color_scheme="amber", variant="soft")),
                width="100%", align_items="center", flex_wrap="wrap",
            ),
            rx.text(product["brand"] + " · " + product["collection"], color=DENIM, font_size="0.76rem", font_weight="700"),
            rx.hstack(
                rx.text(product["price_display"], color=INK, font_weight="700", font_size="1.05rem"),
                width="100%", justify="between", align_items="center",
            ),
            rx.heading(product["name"], font_family=DISPLAY, font_size="1.2rem", color=INK, width="100%", min_height="2.8rem"),
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


def boutique_card(name: str, collection: str, mood: str, description: str, icon_name: str, color: str) -> rx.Component:
    return rx.button(
        rx.vstack(
            rx.hstack(
                rx.center(rx.icon(icon_name, size=19, color=INK), width="42px", height="42px", border_radius="14px", background=color),
                rx.badge("VITRINE FICTÍCIA", color_scheme="gray", variant="soft"),
                width="100%", align="center",
            ),
            rx.text(mood, color=DENIM, font_size="0.72rem", font_weight="800", letter_spacing="0.08em", text_transform="uppercase"),
            rx.heading(name, font_family=DISPLAY, font_size="1.25rem", color=INK, width="100%"),
            rx.text(description, color=MUTED, font_size="0.84rem", line_height="1.55", min_height="4.1rem"),
            rx.hstack(
                rx.text(collection, color=INK, font_size="0.76rem", font_weight="700"),
                rx.spacer(), rx.icon("arrow-down-right", size=17, color=DENIM),
                width="100%", align="center",
            ),
            spacing="3", align_items="flex-start", width="100%",
        ),
        on_click=StoreState.select_boutique(name, collection),
        width="100%", height="100%", display="block", text_align="left", cursor="pointer",
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="22px", padding="1.1rem",
        box_shadow="0 12px 30px rgba(15,26,51,0.05)", transition="transform 220ms ease, box-shadow 220ms ease",
        _hover={"transform": "translateY(-4px)", "box_shadow": "0 20px 40px rgba(15,26,51,0.11)"},
    )


def store_page() -> rx.Component:
    category_options = ["Todas", *STORE_CATEGORIES]
    brand_options = ["Todas", *DEMO_BOUTIQUES, "OSDROUPA"]
    collection_options = ["Todas", *DEMO_COLLECTIONS]
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
                            "Uma curadoria para vestir sua rotina. Explore, salve seus favoritos e acompanhe cada etapa da compra.",
                            color="rgba(248,249,250,0.75)", font_size=["0.95rem", "1.05rem"], max_width="580px", line_height="1.6",
                        ),
                        rx.hstack(
                            rx.link("Explorar coleção", href="#catalogo", background=THREAD, color=INK, padding="0.8rem 1.15rem", border_radius="100px", font_weight="800"),
                            rx.link("Minha sacola · " + StoreState.cart_count.to_string(), href="/carrinho", color=CHALK, font_weight="700"),
                            spacing="4", align="center", flex_wrap="wrap",
                        ),
                        spacing="4", align_items="flex-start",
                    ),
                    width="100%", padding=["1.7rem", "2.5rem", "3.5rem"], border_radius="28px",
                    background=f"linear-gradient(125deg, {INK} 0%, {DENIM} 68%, #526A94 100%)",
                    border="1px solid rgba(233,162,59,0.25)",
                ),
                rx.vstack(
                    rx.vstack(
                        rx.badge("UNIVERSO OSDROUPA", color_scheme="amber", variant="soft"),
                        rx.heading("Quatro vitrines. Muitos jeitos de vestir.", font_family=DISPLAY, color=INK, font_size=["1.6rem", "2rem"]),
                        rx.text("Conheça nossas boutiques fictícias e explore peças demonstrativas com tamanhos, cores, materiais e caimentos descritos.", color=MUTED, max_width="700px", line_height="1.6"),
                        spacing="2", align_items="flex-start",
                    ),
                    rx.grid(
                        boutique_card("Ateliê Entrelinhas", "Alfaiataria expressiva", "Corte e proporção", "Blazers marcados, camisas, saias midi, vestidos e calçados para composições de alfaiataria com personalidade.", "scissors", "#F2E8DA"),
                        boutique_card("Rua Viva Studio", "Cidade em camadas", "Streetwear urbano", "Camisetas amplas, jeans wide leg, bermudas, jaquetas bomber, peças utilitárias e acessórios para o dia a dia.", "sparkles", "#E6E9F2"),
                        boutique_card("Maré de Dentro", "Verão sem pressa", "Resort e textura", "Conjuntos leves, tops transpassados, lenços, saias fluidas, maiô, bolsas e sandálias para combinar do seu jeito.", "sun", "#F6EBD8"),
                        boutique_card("Forma Livre", "Corpo em movimento", "Esportivo cotidiano", "Leggings, tops, polos, corta-vento e tênis em uma seleção demonstrativa com grade ampla de tamanhos.", "activity", "#E4EEE8"),
                        columns={"initial": "1", "sm": "2", "lg": "4"}, spacing="3", width="100%",
                    ),
                    width="100%", spacing="4",
                ),
                rx.grid(
                    rx.box(rx.hstack(rx.center(rx.icon("heart", size=19, color=DENIM), width="42px", height="42px", background="#EEF0F4", border_radius="13px"), rx.vstack(rx.text("Sua curadoria", color=INK, font_weight="700"), rx.text("Salve peças para comparar depois.", color=MUTED, font_size="0.8rem"), spacing="1", align_items="flex-start"), spacing="3", align="center"), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1rem"),
                    rx.box(rx.hstack(rx.center(rx.icon("package-check", size=19, color=DENIM), width="42px", height="42px", background="#EEF0F4", border_radius="13px"), rx.vstack(rx.text("Disponibilidade clara", color=INK, font_weight="700"), rx.text("Veja estoque ou itens sob encomenda.", color=MUTED, font_size="0.8rem"), spacing="1", align_items="flex-start"), spacing="3", align="center"), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1rem"),
                    rx.box(rx.hstack(rx.center(rx.icon("shield-check", size=19, color=DENIM), width="42px", height="42px", background="#EEF0F4", border_radius="13px"), rx.vstack(rx.text("Pedido demonstrativo", color=INK, font_weight="700"), rx.text("Peças fictícias para explorar; nenhum pagamento é processado.", color=MUTED, font_size="0.8rem"), spacing="1", align_items="flex-start"), spacing="3", align="center"), background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1rem"),
                    columns={"initial": "1", "md": "3"}, spacing="3", width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.heading("Escolha com calma.", font_family=DISPLAY, color=INK, font_size="1.7rem"),
                            rx.text("4 boutiques fictícias · " + StoreState.products.length().to_string() + " peças demonstrativas", color=MUTED, font_size="0.9rem"),
                            spacing="1", align_items="flex-start",
                        ),
                        rx.spacer(),
                        rx.input(
                            placeholder="Buscar produto", value=StoreState.store_search,
                            on_change=StoreState.set_store_search, width=["100%", "280px"],
                            background="#FFFFFF", border="1px solid rgba(15,26,51,0.12)", border_radius="100px",
                            padding_x="1rem", height="44px", aria_label="Buscar no catálogo",
                        ),
                        rx.button(
                            rx.hstack(rx.icon("heart", size=16), rx.text("Favoritos"), rx.badge(StoreState.favorite_count, color_scheme="red", variant="soft"), spacing="2"),
                            on_click=StoreState.toggle_favorites_only,
                            background=rx.cond(StoreState.favorites_only, "#FCE8E6", "#FFFFFF"),
                            color=rx.cond(StoreState.favorites_only, ERROR, INK),
                            border="1px solid rgba(15,26,51,0.12)", border_radius="100px", height="44px", padding_x="1rem",
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
                            rx.text("Boutique", font_size="0.75rem", color=MUTED, font_weight="700"),
                            rx.select(brand_options, value=StoreState.brand_filter, on_change=StoreState.set_brand_filter, width=["100%", "220px"]),
                            spacing="1", align_items="flex-start",
                        ),
                        rx.vstack(
                            rx.text("Coleção", font_size="0.75rem", color=MUTED, font_weight="700"),
                            rx.select(collection_options, value=StoreState.collection_filter, on_change=StoreState.set_collection_filter, width=["100%", "220px"]),
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
                    rx.cond(StoreState.cart_feedback != "", rx.text(StoreState.cart_feedback, color=OK, role="status", font_size="0.84rem")),
                    rx.cond(
                        StoreState.products.length() > 0,
                        rx.cond(
                            StoreState.catalog_unclassified_count > 0,
                            rx.box(
                                rx.text(
                                    "Alguns itens foram ocultados porque não têm uma categoria de vestuário válida.",
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
                                        rx.text("O catálogo ainda não tem roupas, calçados ou acessórios disponíveis. Atualize os produtos para exibi-los aqui.", color=MUTED, text_align="center", max_width="620px"),
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
                    spacing="5", width="100%", align_items="stretch", id="catalogo",
                ),
                rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.heading("Um armário com mais intenção.", font_family=DISPLAY, color=CHALK, font_size="1.5rem"),
                            rx.text("A compra é só uma parte: registre suas peças e transforme cada aquisição em novas combinações.", color="rgba(248,249,250,0.72)"),
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
            rx.badge(StoreState.selected_product["product_type"], color_scheme="blue", variant="soft"),
            rx.text(StoreState.selected_product["brand"] + " · " + StoreState.selected_product["collection"], color=DENIM, font_weight="700", font_size="0.84rem"),
            rx.cond(StoreState.selected_product["demonstration"] == "true", rx.badge("Produto demonstrativo", color_scheme="amber", variant="soft")),
            rx.cond(StoreState.selected_product["demonstration"] == "true", rx.callout("Peça e preço para demonstração. A loja confirmará disponibilidade e condições antes de qualquer pagamento.", icon="info", color="amber", width="100%")),
            rx.heading(StoreState.selected_product["name"], font_family=DISPLAY, font_size=["2rem", "2.6rem"], color=INK, line_height="1.08"),
            rx.text(StoreState.selected_product["description"], color=MUTED, line_height="1.7", white_space="pre-wrap"),
            rx.grid(
                rx.vstack(rx.text("Tamanhos", color=MUTED, font_size="0.74rem", font_weight="700"), rx.text(StoreState.selected_product["sizes"], color=INK, font_size="0.86rem"), spacing="1", align_items="flex-start"),
                rx.vstack(rx.text("Cores", color=MUTED, font_size="0.74rem", font_weight="700"), rx.text(StoreState.selected_product["colors"], color=INK, font_size="0.86rem"), spacing="1", align_items="flex-start"),
                rx.vstack(rx.text("Material", color=MUTED, font_size="0.74rem", font_weight="700"), rx.text(StoreState.selected_product["material"], color=INK, font_size="0.86rem"), spacing="1", align_items="flex-start"),
                rx.vstack(rx.text("Caimento", color=MUTED, font_size="0.74rem", font_weight="700"), rx.text(StoreState.selected_product["fit"], color=INK, font_size="0.86rem"), spacing="1", align_items="flex-start"),
                columns={"initial": "1", "sm": "2"}, spacing="3", width="100%",
                background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1rem",
            ),
            rx.text(StoreState.selected_product["price_display"], color=INK, font_family=DISPLAY, font_size="1.8rem", font_weight="700"),
            rx.text(
                rx.cond(
                    StoreState.selected_product["availability"] == "Disponível agora",
                    rx.cond(StoreState.selected_product["stock"] == "1", "1 unidade disponível", StoreState.selected_product["stock"] + " unidades disponíveis"),
                    rx.cond(StoreState.selected_product["availability"] == "Sob encomenda", "Produzido sob encomenda", "Temporariamente indisponível"),
                ),
                color=MUTED, font_size="0.88rem",
            ),
            rx.hstack(
                rx.button(
                    rx.hstack(rx.icon("shopping-bag", size=17), rx.text("Adicionar à sacola"), spacing="2"),
                    on_click=StoreState.add_to_cart(StoreState.selected_product["id"]),
                    disabled=StoreState.selected_product["availability"] == "Sem estoque",
                    background=THREAD, color=INK, border_radius="100px", padding="0.9rem 1.4rem", font_weight="700",
                    _hover={"background": "#F1B958"},
                ),
                rx.button(
                    rx.cond(StoreState.selected_product["favorite"] == "true", rx.icon("heart", fill="currentColor"), rx.icon("heart")),
                    on_click=StoreState.toggle_favorite(StoreState.selected_product["id"]),
                    aria_label=rx.cond(StoreState.selected_product["favorite"] == "true", "Remover dos favoritos", "Salvar nos favoritos"),
                    variant="outline", color=ERROR, border_radius="50%", width="46px", height="46px",
                ),
                spacing="3", align="center", flex_wrap="wrap",
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
                rx.text(item["brand"], color=DENIM, font_size="0.78rem", font_weight="700"),
                rx.cond(item["demonstration"] == "true", rx.badge("Demonstrativo", color_scheme="amber", variant="soft")),
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
            rx.vstack(
                rx.text(device["name"], color=INK, font_weight="700"),
                rx.text(device["type"], color=MUTED, font_size="0.82rem"),
                rx.hstack(rx.icon("clock-3", size=13, color=MUTED), rx.text("Último contato: " + device["last_seen"], color=MUTED, font_size="0.76rem"), spacing="1", flex_wrap="wrap"),
                spacing="1", align_items="flex-start",
            ),
            rx.spacer(), rx.badge(device["status"], color_scheme=rx.cond(device["status"] == "Conectado", "green", rx.cond(device["status"] == "Pareamento pendente", "amber", "gray")), variant="soft"),
            width="100%", align="center", flex_wrap="wrap",
        ),
        href="/dispositivo?id=" + device["id"], background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1rem", width="100%",
        transition="transform 220ms ease, box-shadow 220ms ease",
        _hover={"transform": "translateY(-3px)", "box_shadow": "0 16px 36px rgba(15,26,51,0.08)"},
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
            rx.hstack(rx.vstack(rx.text("ARMÁRIO INTELIGENTE", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.15em"), rx.heading("Dispositivos", font_family=DISPLAY, color=INK, font_size=["2rem", "2.7rem"]), rx.text("Gerencie conexões e consulte eventos do seu armário.", color=MUTED), spacing="2", align_items="flex-start"), rx.spacer(), rx.link("+ Conectar dispositivo", href="/dispositivos/conectar", background=THREAD, color=INK, padding="0.8rem 1.1rem", border_radius="100px", font_weight="700"), width="100%", align="center", flex_wrap="wrap"),
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
                    rx.cond(
                        DeviceState.pairing_is_demo,
                        rx.vstack(
                            rx.callout("Demonstração local: não conecta um dispositivo físico.", icon="info", color="amber", width="100%"),
                            rx.button("Simular confirmação local", on_click=DeviceState.confirm_local_pairing, width="100%", variant="outline", color=DENIM),
                            spacing="2", width="100%",
                        ),
                    ),
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
        width="100%", align="center", flex_wrap="wrap", background="#FFFFFF", border_radius="15px", padding="1rem",
        transition="transform 180ms ease, box-shadow 180ms ease",
        _hover={"transform": "translateY(-2px)", "box_shadow": "0 12px 28px rgba(15,26,51,0.07)"},
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
        transition="transform 220ms ease, box-shadow 220ms ease",
        _hover={"transform": "translateY(-4px)", "box_shadow": "0 18px 40px rgba(15,26,51,0.09)"},
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
        transition="transform 220ms ease, box-shadow 220ms ease",
        _hover={"transform": "translateY(-4px)", "box_shadow": "0 18px 40px rgba(15,26,51,0.09)"},
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
            rx.badge(challenge["category"], color_scheme="amber", variant="soft", size="1"),
            rx.heading(challenge["title"], font_family=DISPLAY, font_size="1.25rem", color=INK),
            rx.text(challenge["description"], color=MUTED, line_height="1.55", min_height="3rem"),
            rx.hstack(rx.text("+" + challenge["points"] + " pontos pessoais", color=DENIM, font_weight="700", font_size="0.84rem"), rx.spacer(), rx.link(challenge["action_label"], href=challenge["action_href"], color=DENIM, font_weight="700", font_size="0.82rem"), width="100%", align="center", flex_wrap="wrap"),
            action,
            spacing="3", align_items="flex-start", width="100%",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.2rem", width="100%",
        transition="transform 220ms ease, box-shadow 220ms ease",
        _hover={"transform": "translateY(-4px)", "box_shadow": "0 18px 40px rgba(15,26,51,0.09)"},
    )


@dataclasses.dataclass
class InspirationPiece:
    papel: str = ""
    nome: str = ""
    descricao: str = ""
    origem: str = ""
    imagem_url: str = ""


@dataclasses.dataclass
class Inspiration:
    id: str = ""
    nome: str = ""
    ocasiao: str = ""
    clima: str = ""
    regiao: str = ""
    estacao: str = ""
    paleta: str = ""
    tecidos: str = ""
    justificativa: str = ""
    nota: str = ""
    imagem: str = ""
    capa_catalogo: str = ""
    status: str = ""
    salvo: bool = False
    pecas: list[InspirationPiece] = dataclasses.field(default_factory=list)


INSPIRATION_FILTER_OCCASIONS = ["Todas", *LOOK_OCCASIONS]
INSPIRATION_FILTER_WEATHER = ["Todos", "Quente", "Ameno", "Frio", "Chuvoso"]
INSPIRATION_FILTER_REGIONS = ["Todas", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]


class InspirationState(AuthState):
    """Feed de inspirações: looks da IA guardados, publicados e moderados (Change 028)."""

    feed: list[Inspiration] = []
    my_created: list[Inspiration] = []
    my_saved: list[Inspiration] = []
    admin_inspirations: list[Inspiration] = []
    feed_tab: str = "descobrir"
    filter_occasion: str = "Todas"
    filter_weather: str = "Todos"
    filter_region: str = "Todas"
    feed_page: int = 1
    feed_has_more: bool = False
    feed_loading: bool = False
    feed_error: str = ""
    feed_notice: str = ""
    publish_candidate_id: str = ""

    @staticmethod
    def _to_inspiration(row: dict) -> Inspiration:
        pieces = [
            InspirationPiece(
                papel=str(p.get("papel") or ""), nome=str(p.get("nome") or ""), descricao=str(p.get("descricao") or ""),
                origem=str(p.get("origem") or ""), imagem_url=str(p.get("imagem_url") or ""),
            )
            for p in (row.get("pecas") or []) if isinstance(p, dict)
        ]
        return Inspiration(
            id=str(row.get("id") or ""), nome=str(row.get("nome") or "Look"), ocasiao=str(row.get("ocasiao") or ""),
            clima=str(row.get("clima") or ""), regiao=str(row.get("regiao") or ""), estacao=str(row.get("estacao") or ""),
            paleta=str(row.get("paleta") or ""), tecidos=str(row.get("tecidos") or ""),
            justificativa=str(row.get("justificativa") or ""), nota=str(row.get("nota") or ""),
            imagem=str(row.get("imagem") or ""),
            capa_catalogo=next((p.imagem_url for p in pieces if p.imagem_url), ""),
            status=str(row.get("status") or ""), salvo=bool(row.get("salvo")), pecas=pieces,
        )

    async def _feed_request(self, method: str, endpoint: str, *, payload: dict | None = None, params: dict | None = None):
        token = self._current_auth_token()
        async with XanoAsyncClient(timeout=XANO_TIMEOUT) as client:
            return await client.request(
                method, f"{XANO_PDB}/{endpoint}",
                headers={"Authorization": f"Bearer {token}"} if token else {},
                json=payload, params=params,
            )

    def _feed_params(self) -> dict:
        params = {"pagina": self.feed_page}
        if self.filter_occasion in LOOK_OCCASIONS:
            params["ocasiao"] = self.filter_occasion
        if self.filter_weather in INSPIRATION_FILTER_WEATHER[1:]:
            params["clima"] = self.filter_weather
        if self.filter_region in INSPIRATION_FILTER_REGIONS[1:]:
            params["regiao"] = self.filter_region
        return params

    async def load_feed(self, append: bool = False):
        self.feed_loading = True
        self.feed_error = ""
        try:
            response = await self._feed_request("GET", "feedInspiracoes", params=self._feed_params())
            response.raise_for_status()
            data = response.json()
            rows = [self._to_inspiration(r) for r in data.get("inspiracoes", []) if isinstance(r, dict)]
            saved_ids = {item.id for item in self.my_saved}
            for item in rows:
                item.salvo = item.id in saved_ids
            self.feed = [*self.feed, *rows] if append else rows
            self.feed_has_more = bool(data.get("tem_mais"))
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            self.feed_error = _xano_failure_message(exc, "Não foi possível carregar o feed de inspirações agora.")
        finally:
            self.feed_loading = False

    async def load_mine(self):
        if not self._current_auth_token():
            self.my_created, self.my_saved = [], []
            return
        try:
            response = await self._feed_request("GET", "minhasInspiracoes")
            response.raise_for_status()
            data = response.json()
            self.my_created = [self._to_inspiration(r) for r in data.get("criadas", []) if isinstance(r, dict)]
            self.my_saved = [self._to_inspiration(r) for r in data.get("salvas", []) if isinstance(r, dict)]
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            self.feed_error = _xano_failure_message(exc, "Não foi possível carregar suas inspirações agora.")

    async def load_inspiration_page(self):
        await self.restore_session()
        self.feed_page = 1
        await self.load_mine()
        await self.load_feed()

    def set_feed_tab(self, value: str | list[str]):
        value = value[0] if isinstance(value, list) and value else value
        if isinstance(value, str) and value in {"descobrir", "minhas"}:
            self.feed_tab = value

    async def _apply_filter(self):
        self.feed_page = 1
        await self.load_feed()

    async def set_filter_occasion(self, value: str):
        if value in INSPIRATION_FILTER_OCCASIONS:
            self.filter_occasion = value
            await self._apply_filter()

    async def set_filter_weather(self, value: str):
        if value in INSPIRATION_FILTER_WEATHER:
            self.filter_weather = value
            await self._apply_filter()

    async def set_filter_region(self, value: str):
        if value in INSPIRATION_FILTER_REGIONS:
            self.filter_region = value
            await self._apply_filter()

    async def load_more(self):
        if self.feed_has_more and not self.feed_loading:
            self.feed_page += 1
            await self.load_feed(append=True)

    async def toggle_saved(self, inspiration_id: str, saved: bool):
        if not self._current_auth_token():
            return rx.redirect("/login")
        if not inspiration_id.isdigit():
            return
        try:
            response = await self._feed_request("DELETE" if saved else "POST", f"inspiracoesSalvas/{inspiration_id}")
            response.raise_for_status()
            self.feed = [dataclasses.replace(i, salvo=not saved) if i.id == inspiration_id else i for i in self.feed]
            await self.load_mine()
            self.feed_notice = "Removida dos salvos." if saved else "Salva nas suas inspirações."
        except (httpx.HTTPError, ValueError) as exc:
            self.feed_error = _xano_failure_message(exc, "Não foi possível atualizar seus salvos.")

    def ask_publish(self, inspiration_id: str):
        self.publish_candidate_id = inspiration_id

    def cancel_publish(self):
        self.publish_candidate_id = ""

    async def confirm_publish(self):
        inspiration_id = self.publish_candidate_id
        self.publish_candidate_id = ""
        if not inspiration_id.isdigit():
            return
        try:
            response = await self._feed_request("POST", f"publicarInspiracao/{inspiration_id}", payload={"autorizo_publicacao": True})
            response.raise_for_status()
            self.feed_notice = "Enviada para revisão. Ela aparece no feed depois de aprovada."
            await self.load_mine()
        except (httpx.HTTPError, ValueError) as exc:
            self.feed_error = _xano_failure_message(exc, "Não foi possível enviar ao feed.")

    async def delete_inspiration(self, inspiration_id: str):
        if not inspiration_id.isdigit():
            return
        try:
            response = await self._feed_request("DELETE", f"minhasInspiracoes/{inspiration_id}")
            response.raise_for_status()
            self.feed_notice = "Inspiração excluída."
            await self.load_mine()
            await self.load_feed()
        except (httpx.HTTPError, ValueError) as exc:
            self.feed_error = _xano_failure_message(exc, "Não foi possível excluir a inspiração.")

    async def load_admin_inspirations(self):
        status = await self._session_gate()
        if status == "login":
            return rx.redirect("/login")
        try:
            response = await self._feed_request("GET", "adminInspiracoes")
            response.raise_for_status()
            self.admin_inspirations = [self._to_inspiration(r) for r in response.json().get("inspiracoes", []) if isinstance(r, dict)]
            self.feed_error = ""
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            self.feed_error = _xano_failure_message(exc, "Não foi possível carregar a fila de inspirações. Acesse com papel admin.")

    async def moderate_inspiration(self, inspiration_id: str, status: str):
        if status not in {"Publicado", "Recusado"} or not inspiration_id.isdigit():
            return
        try:
            response = await self._feed_request("PATCH", f"adminInspiracoes/{inspiration_id}", payload={"status": status})
            response.raise_for_status()
            self.feed_notice = "Inspiração atualizada."
            await self.load_admin_inspirations()
        except (httpx.HTTPError, ValueError) as exc:
            self.feed_error = _xano_failure_message(exc, "Não foi possível moderar a inspiração.")


def inspiration_cover(item: Inspiration) -> rx.Component:
    return rx.cond(
        item.imagem != "",
        rx.image(src=rx.get_upload_url(item.imagem), alt=f"Imagem gerada por IA do look {item.nome}", width="100%", height="280px", object_fit="cover"),
        rx.cond(
            item.capa_catalogo != "",
            rx.center(rx.image(src=item.capa_catalogo, alt=item.nome, height="200px", object_fit="contain"), width="100%", height="280px", background="#F3F0E8"),
            rx.center(rx.icon("sparkles", size=40, color=THREAD), width="100%", height="280px", background=f"linear-gradient(140deg, {INK}, {DENIM})"),
        ),
    )


def inspiration_feed_card(item: Inspiration, owner: bool = False, admin: bool = False) -> rx.Component:
    chips = rx.hstack(
        rx.badge(item.ocasiao, color_scheme="amber", variant="soft", radius="full"),
        rx.cond(item.clima != "", rx.badge(item.clima, variant="soft", radius="full")),
        rx.cond(item.regiao != "", rx.badge(item.regiao, variant="outline", radius="full")),
        rx.cond(item.nota != "", rx.badge(rx.icon("star", size=11), item.nota, color_scheme="green", variant="soft", radius="full")),
        spacing="1", flex_wrap="wrap",
    )
    pieces = rx.vstack(
        rx.foreach(item.pecas, lambda p: rx.text(rx.text.strong(p.papel, ": "), p.nome, color=INK, font_size="0.8rem")),
        spacing="0", width="100%",
    )
    if admin:
        actions = rx.cond(
            item.status == "Pendente",
            rx.hstack(
                rx.button("Publicar", on_click=InspirationState.moderate_inspiration(item.id, "Publicado"), background=OK, color="white", border_radius="100px", size="2"),
                rx.button("Recusar", on_click=InspirationState.moderate_inspiration(item.id, "Recusado"), variant="outline", color=ERROR, border_radius="100px", size="2"),
                spacing="2",
            ),
            rx.badge(item.status, variant="soft"),
        )
    elif owner:
        actions = rx.hstack(
            rx.badge(rx.match(item.status, ("Privado", "Só para você"), ("Pendente", "Em revisão"), ("Publicado", "No feed"), ("Recusado", "Não aprovada"), item.status), color_scheme=rx.match(item.status, ("Publicado", "green"), ("Recusado", "red"), ("Pendente", "amber"), "gray"), variant="soft"),
            rx.spacer(),
            rx.cond((item.status == "Privado") | (item.status == "Recusado"), rx.button(rx.icon("send", size=14), "Enviar ao feed", on_click=InspirationState.ask_publish(item.id), variant="soft", size="1", border_radius="100px")),
            rx.button(rx.icon("trash-2", size=14), on_click=InspirationState.delete_inspiration(item.id), variant="ghost", color=MUTED, size="1", aria_label="Excluir inspiração"),
            width="100%", align="center",
        )
    else:
        actions = rx.button(
            rx.cond(item.salvo, rx.icon("bookmark-check", size=15), rx.icon("bookmark", size=15)),
            rx.cond(item.salvo, "Salva", "Salvar"),
            on_click=InspirationState.toggle_saved(item.id, item.salvo),
            variant=rx.cond(item.salvo, "solid", "outline"), size="2", border_radius="100px",
        )
    return rx.box(
        inspiration_cover(item),
        rx.vstack(
            rx.heading(item.nome, font_family=DISPLAY, color=INK, font_size="1.05rem"),
            chips,
            pieces,
            rx.cond(item.justificativa != "", rx.text(item.justificativa, color=MUTED, font_size="0.8rem", line_height="1.55", style={"display": "-webkit-box", "WebkitLineClamp": "4", "WebkitBoxOrient": "vertical", "overflow": "hidden"})),
            rx.cond(item.imagem != "", rx.text("Imagem gerada por IA (Google Gemini, com marca d'água SynthID).", color=MUTED, font_size="0.7rem")),
            actions,
            spacing="2", padding="1rem", width="100%", align_items="stretch",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", overflow="hidden", width="100%",
    )


def inspiration_feed_section() -> rx.Component:
    filters = rx.grid(
        rx.select(INSPIRATION_FILTER_OCCASIONS, value=InspirationState.filter_occasion, on_change=InspirationState.set_filter_occasion, aria_label="Filtrar por ocasião"),
        rx.select(INSPIRATION_FILTER_WEATHER, value=InspirationState.filter_weather, on_change=InspirationState.set_filter_weather, aria_label="Filtrar por clima"),
        rx.select(INSPIRATION_FILTER_REGIONS, value=InspirationState.filter_region, on_change=InspirationState.set_filter_region, aria_label="Filtrar por região"),
        columns={"initial": "1", "sm": "3"}, spacing="2", width="100%",
    )
    discover = rx.vstack(
        filters,
        rx.cond(
            InspirationState.feed.length() > 0,
            rx.grid(rx.foreach(InspirationState.feed, lambda i: inspiration_feed_card(i)), columns={"initial": "1", "sm": "2", "lg": "3"}, spacing="4", width="100%"),
            rx.cond(~InspirationState.feed_loading, rx.center(rx.text("Ainda não há looks no feed com esses filtros. Gere um look no Look do Dia e compartilhe!", color=MUTED, text_align="center"), padding="2rem", width="100%", background="#FFFFFF", border_radius="20px")),
        ),
        rx.cond(InspirationState.feed_has_more, rx.button("Carregar mais", on_click=InspirationState.load_more, loading=InspirationState.feed_loading, variant="outline", border_radius="100px", align_self="center")),
        spacing="4", width="100%", align_items="stretch",
    )
    publish_confirm = rx.cond(
        InspirationState.publish_candidate_id != "",
        rx.callout(
            rx.vstack(
                rx.text("Ao enviar, este look entra na fila de revisão e, se aprovado, aparece no feed público sem o seu nome. Fotos do seu armário nunca são publicadas; a imagem gerada por IA e as descrições das peças, sim.", font_size="0.85rem"),
                rx.hstack(
                    rx.button("Autorizo a publicação anônima", on_click=InspirationState.confirm_publish, background=INK, color=CHALK, border_radius="100px", size="2"),
                    rx.button("Cancelar", on_click=InspirationState.cancel_publish, variant="ghost", size="2"),
                    spacing="2", flex_wrap="wrap",
                ),
                spacing="2", align_items="flex-start",
            ),
            icon="send", color="amber", width="100%",
        ),
    )
    mine = rx.cond(
        InspirationState.is_authenticated,
        rx.vstack(
            publish_confirm,
            rx.heading("Criadas por você", font_family=DISPLAY, color=INK, font_size="1.2rem"),
            rx.cond(
                InspirationState.my_created.length() > 0,
                rx.grid(rx.foreach(InspirationState.my_created, lambda i: inspiration_feed_card(i, owner=True)), columns={"initial": "1", "sm": "2", "lg": "3"}, spacing="4", width="100%"),
                rx.text("Guarde um look gerado no Look do Dia para vê-lo aqui.", color=MUTED),
            ),
            rx.heading("Salvas do feed", font_family=DISPLAY, color=INK, font_size="1.2rem"),
            rx.cond(
                InspirationState.my_saved.length() > 0,
                rx.grid(rx.foreach(InspirationState.my_saved, lambda i: inspiration_feed_card(i)), columns={"initial": "1", "sm": "2", "lg": "3"}, spacing="4", width="100%"),
                rx.text("Use o botão Salvar nos looks do feed.", color=MUTED),
            ),
            spacing="3", width="100%", align_items="stretch",
        ),
        rx.callout(rx.hstack(rx.text("Entre na sua conta para guardar e compartilhar inspirações."), rx.link("Entrar", href="/login", font_weight="700"), spacing="2"), icon="log-in", width="100%"),
    )
    return rx.vstack(
        rx.hstack(
            rx.vstack(rx.heading("Feed de looks", font_family=DISPLAY, color=INK, font_size="1.6rem"), rx.text("Combinações criadas com o estilista de IA e compartilhadas pela comunidade.", color=MUTED, font_size="0.9rem"), spacing="1", align_items="flex-start"),
            rx.spacer(),
            rx.link("Criar um look", href="/look-do-dia", background=INK, color=CHALK, padding="0.65rem 1.1rem", border_radius="100px", font_weight="700", font_size="0.85rem"),
            width="100%", align="center", flex_wrap="wrap", spacing="3",
        ),
        rx.segmented_control.root(
            rx.segmented_control.item("Descobrir", value="descobrir"),
            rx.segmented_control.item("Minhas inspirações", value="minhas"),
            value=InspirationState.feed_tab, on_change=InspirationState.set_feed_tab,
        ),
        rx.cond(InspirationState.feed_error != "", rx.callout(InspirationState.feed_error, icon="triangle-alert", color="red", width="100%")),
        rx.cond(InspirationState.feed_notice != "", rx.callout(InspirationState.feed_notice, icon="info", color="green", width="100%")),
        rx.cond(InspirationState.feed_tab == "descobrir", discover, mine),
        spacing="4", width="100%", align_items="stretch",
    )


def admin_inspirations_page() -> rx.Component:
    body = rx.cond(
        InspirationState.admin_inspirations.length() > 0,
        rx.grid(rx.foreach(InspirationState.admin_inspirations, lambda i: inspiration_feed_card(i, admin=True)), columns={"initial": "1", "md": "2", "lg": "3"}, spacing="4", width="100%"),
        rx.callout("Não há inspirações para revisar.", icon="badge-check", color="green", width="100%"),
    )
    return rx.box(rx.el.style(CSS), management_navbar(), rx.center(rx.vstack(
        rx.heading("Revisão de inspirações", font_family=DISPLAY, color=INK, font_size="2rem"),
        rx.text("Publique apenas looks adequados ao público. Confira se a imagem gerada não traz pessoas, texto ou conteúdo impróprio.", color=MUTED),
        rx.cond(InspirationState.feed_error != "", rx.callout(InspirationState.feed_error, icon="triangle-alert", color="red", width="100%")),
        rx.cond(InspirationState.feed_notice != "", rx.callout(InspirationState.feed_notice, icon="info", color="green", width="100%")),
        body, spacing="4", width="100%", max_width="1180px", padding_y="2rem", padding_x="1rem", align_items="stretch",
    ), width="100%"), min_height="100vh", background="#F7F5EF", font_family=BODY)


def inspiration_page() -> rx.Component:
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.box(rx.vstack(rx.text("INSPIRAÇÃO", color=THREAD, font_weight="800", font_size="0.72rem", letter_spacing="0.15em"), rx.heading("Vista o seu dia.", font_family=DISPLAY, color=CHALK, font_size=["2.3rem", "3.5rem"]), rx.text("Ideias para encontrar novas combinações dentro do seu próprio armário.", color="rgba(248,249,250,0.8)", max_width="620px", line_height="1.6"), spacing="3", align_items="flex-start"), width="100%", padding=["1.5rem", "2.4rem"], background=f"linear-gradient(120deg, {INK}, {DENIM})", border_radius="24px"),
            inspiration_feed_section(),
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
    challenge_filter_options = ["Todas", "Armário", "Looks", "Cuidado", "Planejamento"]
    status_filter_options = ["Todos", "Em aberto", "Concluídos"]
    return rx.box(
        rx.el.style(CSS), store_navbar(),
        rx.center(rx.vstack(
            rx.box(
                rx.hstack(rx.vstack(rx.text("DESAFIOS PESSOAIS", color=THREAD, font_size="0.72rem", font_weight="800", letter_spacing="0.15em"), rx.heading("Pequenas escolhas, novos caminhos.", font_family=DISPLAY, color=CHALK, font_size=["2rem", "2.7rem"]), rx.text("Atividades para redescobrir peças, cuidar do que você já tem e montar novas combinações.", color="rgba(248,249,250,0.78)", max_width="650px", line_height="1.6"), spacing="2", align_items="flex-start"), rx.spacer(), rx.vstack(rx.text(ContentState.challenge_points, font_family=DISPLAY, font_size="2rem", font_weight="800", color=INK), rx.text("PONTOS PESSOAIS", font_size="0.65rem", font_weight="800", color=MUTED, letter_spacing="0.1em"), spacing="0", align="center", background="#FFFFFF", border_radius="18px", padding="0.9rem 1.2rem"), width="100%", align="center", flex_wrap="wrap"),
                width="100%", padding=["1.4rem", "2rem"], border_radius="24px", background=f"linear-gradient(120deg, {INK}, {DENIM})",
            ),
            rx.callout(ContentState.challenge_sync_message + " · Conclua cada atividade quando realmente tiver feito.", icon="info", color="blue", width="100%"),
            rx.box(
                rx.vstack(rx.hstack(rx.text("Progresso dos desafios", color=INK, font_weight="700"), rx.spacer(), rx.text(ContentState.challenge_completion_percent.to_string() + "% · " + ContentState.completed_challenges.length().to_string() + "/" + str(len(WARDROBE_CHALLENGES)), color=MUTED), width="100%"), rx.box(rx.box(height="100%", width=ContentState.challenge_completion_percent.to_string() + "%", background=THREAD, border_radius="999px", transition="width 320ms ease"), width="100%", height="9px", background="rgba(15,26,51,0.09)", border_radius="999px", overflow="hidden", role="progressbar", aria_label="Progresso dos desafios pessoais"), spacing="2", width="100%"),
                background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="18px", padding="1rem", width="100%",
            ),
            rx.hstack(
                rx.vstack(rx.text("Tema", color=MUTED, font_size="0.75rem", font_weight="700"), rx.select(challenge_filter_options, value=ContentState.challenge_category_filter, on_change=ContentState.set_challenge_category_filter, width=["100%", "220px"]), spacing="1", align_items="stretch"),
                rx.vstack(rx.text("Andamento", color=MUTED, font_size="0.75rem", font_weight="700"), rx.select(status_filter_options, value=ContentState.challenge_status_filter, on_change=ContentState.set_challenge_status_filter, width=["100%", "190px"]), spacing="1", align_items="stretch"),
                rx.spacer(), rx.link("Ver meus pontos e níveis", href="/fidelidade", color=DENIM, font_weight="700"),
                width="100%", align="end", flex_wrap="wrap", spacing="3",
            ),
            rx.cond(ContentState.filtered_challenge_cards.length() > 0, rx.grid(rx.foreach(ContentState.filtered_challenge_cards, challenge_card), columns={"initial": "1", "md": "2"}, spacing="4", width="100%"), rx.center(rx.vstack(rx.icon("list-filter", size=30, color=DENIM), rx.text("Não há desafios nessa seleção.", color=MUTED), rx.button("Limpar filtros", on_click=ContentState.reset_challenge_filters, variant="ghost", color=DENIM), spacing="2", align="center"), width="100%", min_height="200px", background="#FFFFFF", border_radius="18px")),
            spacing="5", width="100%", max_width="1120px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


def management_navbar() -> rx.Component:
    links = [
        ("Vis\u00e3o geral", "/gestao", "layout-dashboard"),
        ("Produtos", "/gestao/produtos", "shirt"),
        ("Pedidos", "/gestao/pedidos", "package-check"),
        ("Clientes", "/gestao/clientes", "users-round"),
        ("Relat\u00f3rios", "/gestao/relatorios", "chart-no-axes-combined"),
        ("Depoimentos", "/gestao/depoimentos", "messages-square"),
        ("Privacidade", "/gestao/privacidade", "shield-check"),
        ("Alfaiataria", "/gestao/alfaiataria", "scissors"),
        ("Inspirações", "/gestao/inspiracoes", "images"),
    ]
    nav_links = [
        rx.link(
            rx.hstack(rx.icon(icon, size=15), rx.text(label), spacing="2", align="center"),
            href=href,
            class_name="osd-nav-primary",
        )
        for label, href, icon in links
    ]
    mobile_links = [
        rx.link(
            rx.hstack(rx.icon(icon, size=15), rx.text(label), spacing="2", align="center"),
            href=href,
            class_name="osd-nav-pill",
            font_size="0.8rem",
        )
        for label, href, icon in links
    ]
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.link(
                    rx.hstack(
                        rx.box(rx.html(LOGO_SVG), class_name="osd-brand-mark"),
                        rx.vstack(
                            rx.text("OSDROUPA", font_family=DISPLAY, font_weight="800", color=CHALK, letter_spacing="0.055em"),
                            rx.text("CENTRAL DE GEST\u00c3O", font_size="0.55rem", font_weight="700", color=THREAD, letter_spacing="0.12em"),
                            spacing="0",
                            align_items="flex-start",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    href="/gestao",
                ),
                rx.spacer(),
                rx.link(
                    rx.hstack(rx.icon("arrow-left", size=15), rx.text("Voltar \u00e0 loja"), spacing="2"),
                    href="/loja",
                    color=CHALK,
                    font_size="0.82rem",
                    font_weight="700",
                    padding="0.58rem 0.9rem",
                    border="1px solid rgba(255,255,255,.14)",
                    border_radius="999px",
                    _hover={"color": THREAD, "background": "rgba(255,255,255,.07)"},
                ),
                width="100%",
                align="center",
                class_name="osd-header-primary",
            ),
            rx.hstack(*nav_links, spacing="5", align="center", display=["none", "none", "none", "none", "flex"], class_name="osd-header-secondary"),
            rx.box(
                rx.hstack(*mobile_links, spacing="2", width="max-content", min_width="100%", align="center"),
                class_name="osd-mobile-nav",
                overflow_x="auto",
                width="100%",
                padding_y="0.35rem",
                display=["block", "block", "block", "block", "none"],
            ),
            spacing="0",
            width="100%",
            max_width="1320px",
            margin_x="auto",
        ),
        class_name="osd-site-header",
        padding_x=["1rem", "1.5rem", "2rem"],
        width="100%",
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
                        rx.button("Tentar novamente", on_click=ManagementState.retry_management, variant="outline", color=DENIM),
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
        transition="transform 220ms ease, box-shadow 220ms ease",
        _hover={"transform": "translateY(-3px)", "box_shadow": "0 16px 36px rgba(15,26,51,0.08)"},
    )


def management_status_buttons(row: dict, first: str, second: str = "") -> rx.Component:
    return rx.hstack(
        rx.button(first, on_click=ManagementState.change_order_status(row["id"], first), size="2", variant="outline", color=DENIM),
        rx.cond(second != "", rx.button(second, on_click=ManagementState.change_order_status(row["id"], second), size="2", variant="outline", color=ERROR)),
        spacing="2", flex_wrap="wrap",
    )


def management_row_card(row: dict) -> rx.Component:
    return rx.hstack(
        rx.vstack(rx.text(row["name"], color=INK, font_weight="700"), rx.text("#" + row["id"], color=MUTED, font_size="0.74rem"), spacing="1", align_items="flex-start"),
        rx.spacer(), rx.badge(row["status"], color_scheme="amber", variant="soft"),
        rx.text(row["detail"], color=INK, font_weight="600"),
        rx.cond(row["status"] == "Aguardando confirmação", management_status_buttons(row, "Confirmado", "Cancelado"),
        rx.cond(row["status"] == "Confirmado", management_status_buttons(row, "Em preparo", "Cancelado"),
        rx.cond(row["status"] == "Em preparo", management_status_buttons(row, "Enviado"),
        rx.cond(row["status"] == "Enviado", management_status_buttons(row, "Entregue"))))),
        width="100%", align="center", flex_wrap="wrap", background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="16px", padding="1rem",
        transition="transform 180ms ease, box-shadow 180ms ease",
        _hover={"transform": "translateY(-2px)", "box_shadow": "0 12px 28px rgba(15,26,51,0.07)"},
    )


def management_dashboard_page() -> rx.Component:
    body = rx.vstack(
        rx.grid(rx.foreach(ManagementState.management_metrics, management_metric_card), columns={"initial": "1", "sm": "2", "lg": "4"}, spacing="4", width="100%"),
        rx.grid(
            rx.link(rx.vstack(rx.icon("package", size=26, color=DENIM), rx.heading("Catálogo", font_family=DISPLAY, color=INK), rx.text("Produtos e disponibilidade", color=MUTED), spacing="2", align_items="flex-start"), href="/gestao/produtos", background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.4rem", width="100%", transition="transform 220ms ease, box-shadow 220ms ease", _hover={"transform": "translateY(-3px)", "box_shadow": "0 16px 36px rgba(15,26,51,0.08)"}),
            rx.link(rx.vstack(rx.icon("clipboard-list", size=26, color=DENIM), rx.heading("Pedidos", font_family=DISPLAY, color=INK), rx.text("Fila e acompanhamento", color=MUTED), spacing="2", align_items="flex-start"), href="/gestao/pedidos", background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.4rem", width="100%", transition="transform 220ms ease, box-shadow 220ms ease", _hover={"transform": "translateY(-3px)", "box_shadow": "0 16px 36px rgba(15,26,51,0.08)"}),
            rx.link(rx.vstack(rx.icon("users", size=26, color=DENIM), rx.heading("Clientes", font_family=DISPLAY, color=INK), rx.text("Contas e relacionamento", color=MUTED), spacing="2", align_items="flex-start"), href="/gestao/clientes", background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.4rem", width="100%", transition="transform 220ms ease, box-shadow 220ms ease", _hover={"transform": "translateY(-3px)", "box_shadow": "0 16px 36px rgba(15,26,51,0.08)"}),
            rx.link(rx.vstack(rx.icon("chart-no-axes-combined", size=26, color=DENIM), rx.heading("Relatórios", font_family=DISPLAY, color=INK), rx.text("Histórico operacional por pedido", color=MUTED), spacing="2", align_items="flex-start"), href="/gestao/relatorios", background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.4rem", width="100%", transition="transform 220ms ease, box-shadow 220ms ease", _hover={"transform": "translateY(-3px)", "box_shadow": "0 16px 36px rgba(15,26,51,0.08)"}),
            columns={"initial": "1", "md": "2", "lg": "4"}, spacing="4", width="100%",
        ),
        spacing="5", width="100%",
    )
    return management_shell("Visão geral", "Acompanhe a operação diária do OSDROUPA.", body)


def management_list_page(title: str, subtitle: str) -> rx.Component:
    body = rx.cond(
        ManagementState.management_rows.length() == 0,
        rx.center(rx.vstack(rx.icon("inbox", size=34, color=DENIM), rx.text("Ainda não há registros para exibir.", color=MUTED), spacing="3", align_items="center"), width="100%", min_height="220px", background="#FFFFFF", border_radius="20px"),
        rx.vstack(
            rx.foreach(ManagementState.management_rows, management_row_card),
            rx.hstack(
                rx.button("Anterior", on_click=ManagementState.previous_management_page, variant="outline", disabled=ManagementState.management_page <= 1),
                rx.text(ManagementState.management_page, "ª página", color=MUTED, font_weight="600"),
                rx.button("Próxima", on_click=ManagementState.next_management_page, variant="outline", disabled=~ManagementState.management_has_next),
                width="100%", justify="center", spacing="3", padding_top="1rem",
            ),
            spacing="3", width="100%", align_items="stretch",
        ),
    )
    return management_shell(title, subtitle, body)


def management_pagination() -> rx.Component:
    return rx.hstack(
        rx.button("Anterior", on_click=ManagementState.previous_management_page, variant="outline", disabled=ManagementState.management_page <= 1),
        rx.text(ManagementState.management_page, "ª página", color=MUTED, font_weight="600"),
        rx.button("Próxima", on_click=ManagementState.next_management_page, variant="outline", disabled=~ManagementState.management_has_next),
        width="100%", justify="center", spacing="3", padding_top="1rem",
    )


def management_products_page() -> rx.Component:
    product_form = rx.box(
        rx.vstack(
            rx.heading("Novo produto", font_family=DISPLAY, color=INK, font_size="1.35rem"),
            rx.grid(
                field("Nome", value=ManagementState.product_name, on_change=ManagementState.set_product_name, placeholder="Camisa de linho"),
                rx.vstack(_label("Categoria"), rx.select(list(STORE_CATEGORIES), value=ManagementState.product_category, on_change=ManagementState.set_product_category, width="100%"), spacing="1", align_items="stretch", width="100%"),
                field("Boutique / marca", value=ManagementState.product_brand, on_change=ManagementState.set_product_brand, placeholder="Ateliê Entrelinhas"),
                field("Coleção", value=ManagementState.product_collection, on_change=ManagementState.set_product_collection, placeholder="Alfaiataria expressiva"),
                field("Tipo de peça", value=ManagementState.product_type, on_change=ManagementState.set_product_type, placeholder="Blazer, vestido, tênis..."),
                field("Preço (R$)", value=ManagementState.product_price, on_change=ManagementState.set_product_price, type="number", min="0", step="0.01", placeholder="189,00"),
                field("Estoque", value=ManagementState.product_stock, on_change=ManagementState.set_product_stock, type="number", min="0", step="1", placeholder="10"),
                columns={"initial": "1", "sm": "2"}, spacing="3", width="100%",
            ),
            rx.grid(
                field("Tamanhos", value=ManagementState.product_sizes, on_change=ManagementState.set_product_sizes, placeholder="PP, P, M, G, GG"),
                field("Cores", value=ManagementState.product_colors, on_change=ManagementState.set_product_colors, placeholder="Azul, areia, preto"),
                field("Material", value=ManagementState.product_material, on_change=ManagementState.set_product_material, placeholder="Malha de algodão"),
                field("Caimento", value=ManagementState.product_fit, on_change=ManagementState.set_product_fit, placeholder="Amplo; cintura alta"),
                columns={"initial": "1", "sm": "2"}, spacing="3", width="100%",
            ),
            field("Descrição", value=ManagementState.product_description, on_change=ManagementState.set_product_description, placeholder="Detalhes do tecido e caimento"),
            field("Imagem (URL HTTPS ou /products/arquivo.svg)", value=ManagementState.product_image_url, on_change=ManagementState.set_product_image_url, placeholder="/products/linen-shirt.svg"),
            rx.vstack(
                _label("Modo de venda"),
                rx.select(
                    ["Demonstração sem cobrança", "Venda real · Mercado Pago"],
                    value=ManagementState.product_sale_mode,
                    on_change=ManagementState.set_product_demonstration,
                    width="100%",
                ),
                rx.text("Produtos demonstrativos não geram cobrança. A venda real exige as credenciais do Mercado Pago no servidor.", color=MUTED, font_size="0.8rem"),
                spacing="1", width="100%", align_items="stretch",
            ),
            rx.cond(ManagementState.product_action_message != "", rx.text(ManagementState.product_action_message, color=rx.cond(ManagementState.product_action_error, ERROR, OK), font_size="0.84rem")),
            rx.button("Cadastrar produto", on_click=ManagementState.create_product, loading=ManagementState.product_action_loading, background=INK, color=CHALK, border_radius="100px", font_weight="700"),
            spacing="3", align_items="stretch", width="100%",
        ),
        background="#FFFFFF", border="1px solid rgba(15,26,51,0.08)", border_radius="20px", padding="1.4rem", width="100%",
    )
    listings = rx.cond(
        ManagementState.management_rows.length() == 0,
        rx.center(rx.text("Ainda não há produtos no catálogo.", color=MUTED), width="100%", min_height="120px", background="#FFFFFF", border_radius="20px"),
        rx.vstack(rx.foreach(ManagementState.management_rows, management_row_card), management_pagination(), spacing="3", width="100%", align_items="stretch"),
    )
    body = rx.vstack(product_form, listings, spacing="4", width="100%", align_items="stretch")
    return management_shell("Catálogo e estoque", "Cadastre produtos e acompanhe a disponibilidade no catálogo local.", body)


def management_orders_page() -> rx.Component:
    body = rx.vstack(
        rx.cond(ManagementState.order_action_message != "", rx.callout(ManagementState.order_action_message, icon="info", color="green", width="100%")),
        rx.cond(ManagementState.management_rows.length() == 0, rx.center(rx.text("Ainda não há pedidos para exibir.", color=MUTED), width="100%", min_height="160px", background="#FFFFFF", border_radius="20px"), rx.vstack(rx.foreach(ManagementState.management_rows, management_row_card), management_pagination(), spacing="3", width="100%", align_items="stretch")),
        spacing="3", width="100%", align_items="stretch",
    )
    return management_shell("Fila de pedidos", "Atualize o status operacional; o painel não confirma pagamentos.", body)


def management_customers_page() -> rx.Component:
    return management_list_page("Clientes", "Consulte contas atendidas pela operação.")


def management_reports_page() -> rx.Component:
    return management_list_page("Relatórios", "Histórico operacional por pedido. Indicadores financeiros entram após a conciliação de pagamentos.")


def checkout_summary_line(item: dict) -> rx.Component:
    return rx.hstack(
        rx.vstack(rx.text(item["name"], color=INK, font_weight="700", font_size="0.88rem"), rx.text(item["quantity"] + " × " + item["unit_price"], color=MUTED, font_size="0.76rem"), spacing="1", align_items="flex-start"),
        rx.spacer(), rx.text(item["line_total"], color=INK, font_weight="700", font_size="0.86rem"),
        width="100%", align="center", padding_y="0.6rem", border_bottom="1px solid rgba(15,26,51,0.06)",
    )


def checkout_page() -> rx.Component:
    checkout_form = rx.grid(
        rx.vstack(
            rx.hstack(rx.badge("ETAPA 2 DE 3", color_scheme="amber", variant="soft"), rx.text("Entrega", color=MUTED, font_size="0.82rem", font_weight="700"), spacing="2", align="center"),
            rx.heading("Onde você quer receber?", font_family=DISPLAY, color=INK, font_size="1.45rem"),
            rx.text("Escolha um endereço salvo na sua conta. Prazo e frete serão confirmados conforme a operação da loja.", color=MUTED, line_height="1.55"),
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
            rx.cond(
                OrdersState.checkout_mode == "demonstracao",
                rx.vstack(
                    rx.heading("Confirmação da loja", font_family=DISPLAY, color=INK, font_size="1.35rem"),
                    rx.callout("Este pedido registra seu interesse. A loja confirmará disponibilidade, prazo e preço; nenhum pagamento será cobrado agora.", icon="store", color="amber", width="100%"),
                    width="100%", align_items="stretch", spacing="3",
                ),
                rx.vstack(
                    rx.hstack(rx.badge("ETAPA 3 DE 3", color_scheme="amber", variant="soft"), rx.heading("Pagamento", font_family=DISPLAY, color=INK, font_size="1.35rem"), spacing="2", align="center"),
                    rx.hstack(
                        rx.icon("shield-check", size=22, color=DENIM),
                        rx.vstack(
                            rx.text("Finalize no ambiente do Mercado Pago", color=INK, font_weight="700"),
                            rx.text("As formas de pagamento habilitadas para esta compra serão mostradas lá. Pix ou cartão podem aparecer conforme a configuração da conta vendedora.", color=MUTED, font_size="0.82rem", line_height="1.5"),
                            spacing="1", align_items="flex-start",
                        ),
                        align_items="center", spacing="3", width="100%",
                        padding="1rem", border="1px solid rgba(15,26,51,0.12)", border_radius="16px",
                    ),
                    width="100%", align_items="stretch", spacing="3",
                ),
            ),
            rx.cond(OrdersState.checkout_mode != "demonstracao", rx.callout("O OSDROUPA não coleta nem guarda número de cartão. O pedido só muda para pago após confirmação do webhook do Mercado Pago.", icon="lock-keyhole", color="green", width="100%")),
            rx.cond(OrdersState.checkout_mixed_cart, rx.callout("A sacola mistura produtos demonstrativos e produtos reais. Finalize em pedidos separados.", icon="triangle_alert", color="red", width="100%")),
            rx.cond(
                OrdersState.checkout_error != "",
                rx.callout(OrdersState.checkout_error, icon="triangle_alert", color="red", width="100%"),
            ),
            rx.cond(
                OrdersState.checkout_notice != "",
                rx.callout(OrdersState.checkout_notice, icon="info", color="amber", width="100%"),
            ),
            rx.button(
                rx.cond(OrdersState.checkout_submitting, "Validando pedido…", rx.cond(OrdersState.checkout_mode == "demonstracao", "Enviar pedido demonstrativo", "Revisar pedido e ir ao pagamento")),
                on_click=OrdersState.submit_checkout,
                loading=OrdersState.checkout_submitting,
                disabled=(OrdersState.checkout_cart_count == 0) | (OrdersState.checkout_addresses.length() == 0) | OrdersState.checkout_mixed_cart,
                width="100%", background=THREAD, color=INK, border_radius="100px", font_weight="700",
            ),
            rx.text("Preço, estoque e total são conferidos pelo servidor. O navegador não confirma pagamento nem envia um valor final confiável.", color=MUTED, font_size="0.78rem", line_height="1.5"),
            spacing="4", align_items="stretch", width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.heading("Resumo do pedido", font_family=DISPLAY, color=INK, font_size="1.25rem"),
                rx.hstack(rx.text("Itens na sacola", color=MUTED), rx.spacer(), rx.text(OrdersState.checkout_cart_count, color=INK, font_weight="700"), width="100%"),
                rx.vstack(rx.foreach(OrdersState.checkout_display_items, checkout_summary_line), spacing="0", width="100%", align_items="stretch"),
                rx.divider(),
                rx.hstack(rx.text("Subtotal estimado", color=INK, font_weight="700"), rx.spacer(), rx.text(OrdersState.checkout_subtotal_display, color=INK, font_weight="800"), width="100%"),
                rx.text("Estimativa da sacola. Frete, disponibilidade e preço final são recalculados pelo servidor e confirmados pela loja.", color=MUTED, font_size="0.8rem", line_height="1.5"),
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
            rx.badge(rx.cond(OrdersState.checkout_mode == "demonstracao", "PEDIDO DE DEMONSTRAÇÃO", "AGUARDANDO CONFIRMAÇÃO DO PAGAMENTO"), color_scheme=rx.cond(OrdersState.checkout_mode == "demonstracao", "amber", "blue"), variant="soft"),
            rx.heading(rx.cond(OrdersState.checkout_mode == "demonstracao", "Pedido enviado para confirmação", "Pedido criado · pagamento pendente"), font_family=DISPLAY, color=INK, text_align="center"),
            rx.text(rx.cond(OrdersState.checkout_mode == "demonstracao", "A loja ainda precisa confirmar disponibilidade, prazo e preço. Nenhum pagamento foi realizado.", "O pedido foi registrado. A confirmação só ocorre depois da consulta segura do webhook Mercado Pago."), color=MUTED, text_align="center"),
            rx.text("Pedido #" + OrdersState.checkout_order_id, color=INK, font_weight="700"),
            rx.cond(OrdersState.checkout_url != "", rx.link("Abrir checkout Mercado Pago", href=OrdersState.checkout_url, is_external=True, background=THREAD, color=INK, padding="0.85rem 1.2rem", border_radius="100px", font_weight="800")),
            rx.cond(OrdersState.checkout_url != "", rx.text("Depois de pagar, volte ao OSDROUPA e atualize Meus pedidos para acompanhar a confirmação.", color=MUTED, font_size="0.84rem", text_align="center", max_width="520px")),
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
            rx.hstack(
                rx.badge("1 · Sacola", color_scheme="green", variant="soft"),
                rx.badge("2 · Entrega", color_scheme="amber", variant="soft"),
                rx.badge("3 · Pagamento", color_scheme=rx.cond(OrdersState.checkout_mode == "demonstracao", "gray", "blue"), variant="soft"),
                spacing="2", flex_wrap="wrap", width="100%",
            ),
        rx.vstack(
            rx.heading("Finalizar pedido", font_family=DISPLAY, color=INK, font_size=["2rem", "2.5rem"]),
            rx.text(rx.cond(OrdersState.checkout_mode == "demonstracao", "Pedido de demonstração com confirmação posterior da loja.", "Entrega e pagamento pelo Mercado Pago."), color=MUTED),
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
                rx.badge(order["payment_status"], color_scheme=rx.cond(order["paid"] == "true", "green", "gray"), variant="soft"),
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
                        rx.hstack(rx.text("Pagamento", color=MUTED), rx.spacer(), rx.badge(OrdersState.order_detail["payment_status"], color_scheme=rx.cond(OrdersState.order_detail["paid"] == "true", "green", "gray"), variant="soft"), width="100%"),
                        rx.hstack(rx.text("Total", color=INK, font_weight="700"), rx.spacer(), rx.text("R$ " + OrdersState.order_detail["total"], color=INK, font_weight="700", font_size="1.2rem"), width="100%"),
                        rx.cond(OrdersState.order_checkout_url != "", rx.link("Continuar pagamento no Mercado Pago", href=OrdersState.order_checkout_url, is_external=True, color=DENIM, font_weight="700")),
                        rx.text("O pagamento só aparece como confirmado após validação do webhook Mercado Pago.", color=MUTED, font_size="0.82rem"),
                        spacing="4", width="100%", align_items="stretch", background="#FFFFFF", border_radius="22px", padding="1.5rem",
                    ),
                ),
            ),
            spacing="4", width="100%", max_width="900px", padding_y=["1.5rem", "2.5rem"], padding_x=["1rem", "1.5rem", "2rem"],
        ), width="100%"),
        min_height="100vh", background="#F7F5EF", font_family=BODY,
    )


payment_api = FastAPI()


@payment_api.post("/api/webhooks/mercadopago")
async def mercadopago_webhook(request: Request):
    if os.environ.get("OSDROUPA_BACKEND", "sqlite").strip().lower() != "sqlite":
        return JSONResponse({"message": "O webhook Mercado Pago ainda está conectado ao backend SQLite local."}, status_code=503)
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse({"message": "Corpo JSON inválido."}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"message": "Formato de notificação inválido."}, status_code=400)
    event_type = str(payload.get("type") or request.query_params.get("type") or "").lower()
    if event_type not in {"order", "orders"}:
        return JSONResponse({"ok": True, "ignored": True}, status_code=200)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    data_id = str(request.query_params.get("data.id") or data.get("id") or "").strip()
    if not data_id:
        return JSONResponse({"message": "Identificador da Order ausente."}, status_code=400)
    from professormateria.local_backend import local_backend

    result, status_code = await asyncio.to_thread(
        local_backend.process_mercadopago_webhook,
        request.headers.get("x-signature", ""),
        request.headers.get("x-request-id", ""),
        data_id,
        str(payload.get("id") or f"{event_type}:{data_id}"),
    )
    return JSONResponse(result, status_code=status_code)


app = rx.App(
    stylesheets=[FONTS],
    api_transformer=payment_api,
)
app.add_page(index, route="/", title="OSDROUPA | Guarda-Roupa Inteligente & Alfaiataria Conectada", on_load=AuthState.restore_session)
app.add_page(services_page, route="/servicos", title="Serviços e Alfaiataria | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(novelties_page, route="/novidades", title="Novidades | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(testimonials_page, route="/depoimentos", title="Histórias da Comunidade | OSDROUPA", on_load=WardrobeLifeState.load_testimonials)
app.add_page(how_it_works_page, route="/como-funciona", title="Como Funciona | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(login_page, route="/login", title="Entrar | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(signup_page, route="/cadastro", title="Criar Conta | OSDROUPA", on_load=AuthState.restore_session)
app.add_page(reset_password_page, route="/redefinir-senha", title="Redefinir senha | OSDROUPA", on_load=AuthState.load_reset_page)
app.add_page(profile_page, route="/perfil", title="Meu Perfil | OSDROUPA", on_load=AuthState.load_profile_page)
app.add_page(wardrobe_page, route="/armario", title="Meu Armário | OSDROUPA", on_load=WardrobeState.load_wardrobe)
app.add_page(looks_page, route="/looks", title="Meus Looks | OSDROUPA", on_load=LookState.load_looks)
app.add_page(calendar_page, route="/calendario", title="Calendário de Looks | OSDROUPA", on_load=LookState.load_looks)
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
app.add_page(admin_testimonials_page, route="/gestao/depoimentos", title="Moderação de depoimentos | OSDROUPA", on_load=WardrobeLifeState.load_admin_testimonials)
app.add_page(admin_privacy_page, route="/gestao/privacidade", title="Solicitações de privacidade | OSDROUPA", on_load=WardrobeLifeState.load_admin_privacy_requests)
app.add_page(admin_tailoring_page, route="/gestao/alfaiataria", title="Pedidos de alfaiataria | OSDROUPA", on_load=WardrobeLifeState.load_admin_tailoring_requests)
app.add_page(daily_look_page, route="/look-do-dia", title="Look do dia | OSDROUPA", on_load=[WardrobeLifeState.load_weather_context, WardrobeLifeState.load_daily_look])
app.add_page(loyalty_page, route="/fidelidade", title="Fidelidade | OSDROUPA", on_load=WardrobeLifeState.load_fidelity)
app.add_page(usage_history_page, route="/historico-uso", title="Histórico de uso | OSDROUPA", on_load=WardrobeLifeState.load_usage_history)
app.add_page(packing_page, route="/malas", title="Mala inteligente | OSDROUPA", on_load=WardrobeLifeState.load_travel_planner)
app.add_page(tryon_page, route="/provador", title="Provador de combinações | OSDROUPA", on_load=WardrobeLifeState.load_tryon)
app.add_page(tailoring_request_page, route="/servicos/solicitar", title="Solicitar ajuste | OSDROUPA", on_load=WardrobeLifeState.load_service_requests)
app.add_page(privacy_page, route="/privacidade", title="Política de Privacidade | OSDROUPA", on_load=WardrobeLifeState.load_privacy_page)
app.add_page(inspiration_page, route="/inspiracao", title="Inspiração | OSDROUPA", on_load=InspirationState.load_inspiration_page)
app.add_page(admin_inspirations_page, route="/gestao/inspiracoes", title="Moderação de inspirações | OSDROUPA", on_load=InspirationState.load_admin_inspirations)
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
