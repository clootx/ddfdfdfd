import reflex as rx

config = rx.Config(
    app_name="OSDroupa",
    plugins=[
        rx.plugins.TailwindV3Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(appearance="light", accent_color="amber", radius="large")
        ),
    ],
)
