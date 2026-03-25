import reflex as rx

from receipt_ai.components.chat_components import (
    chat_center_panel,
    chat_history,
    recent_chats_panel,
)
from receipt_ai.components.navigation import top_nav
from receipt_ai.core.constants import APP_BACKGROUND, APP_FOREGROUND, BORDER_COLOR


def chat_page() -> rx.Component:
    return rx.box(
        top_nav("chat"),
        rx.hstack(
            rx.box(
                chat_history(),
                width="22%",
                min_width="240px",
                padding="1rem",
                border_right=f"1px solid {BORDER_COLOR}",
            ),
            rx.box(
                chat_center_panel(),
                recent_chats_panel(),
                width="78%",
                padding="1rem",
            ),
            width="100%",
            align="start",
            min_height="calc(100vh - 74px)",
        ),
        bg=APP_BACKGROUND,
        color=APP_FOREGROUND,
        min_height="100vh",
    )
