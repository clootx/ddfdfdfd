import reflex as rx

from OSDroupa.env import load_project_env

# Carrega o .env antes do Reflex ler a configuração; variáveis do terminal têm prioridade.
load_project_env()

config = rx.Config(
    app_name="OSDroupa",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV3Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(appearance="light", accent_color="amber", radius="large")
        ),
    ],
)
