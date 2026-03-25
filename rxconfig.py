import reflex as rx

config = rx.Config(
    app_name="receipt_ai",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)