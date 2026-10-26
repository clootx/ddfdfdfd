import reflex as rx

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
