"""Branded 404 route (Phase 10)."""

import reflex as rx

from receipt_ai.components.navigation import top_nav
from receipt_ai.components.skip_link import skip_to_main
from receipt_ai.core.constants import APP_BACKGROUND, APP_FOREGROUND, MUTED_TEXT
from receipt_ai.core.theme.a11y import A11Y_GLOBAL_CSS


def not_found_page() -> rx.Component:
    """Unknown routes: friendly copy and navigation home."""
    return rx.box(
        skip_to_main(),
        top_nav(""),
        rx.el.style(A11Y_GLOBAL_CSS),
        rx.el.main(
            rx.center(
                rx.vstack(
                    rx.heading("404", size="9", weight="bold"),
                    rx.text("Page not found", size="5", weight="medium"),
                    rx.text(
                        "The page you are looking for does not exist or was moved.",
                        color=MUTED_TEXT,
                        text_align="center",
                        max_width="420px",
                    ),
                    rx.hstack(
                        rx.link(
                            rx.button("Go to Files", color_scheme="green", size="3"),
                            href="/",
                        ),
                        rx.link(
                            rx.button("Go to Chat", variant="outline", size="3"),
                            href="/chat",
                        ),
                        spacing="3",
                        margin_top="0.5rem",
                    ),
                    spacing="3",
                    align="center",
                ),
                width="100%",
                min_height="55vh",
                padding="2rem 1rem",
            ),
            id="main-content",
            tab_index=-1,
            width="100%",
            flex="1",
            outline="none",
        ),
        bg=APP_BACKGROUND,
        color=APP_FOREGROUND,
        min_height="100vh",
        display="flex",
        flex_direction="column",
    )
