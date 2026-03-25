import reflex as rx

from receipt_ai.components.ui.buttons import nav_button
from receipt_ai.core.constants import BORDER_COLOR, PANEL_BG, SECONDARY_TEXT


def top_nav(active_page: str) -> rx.Component:
    """Top navigation bar shared across pages."""
    return rx.hstack(
        # Brand section (left).
        rx.hstack(
            rx.heading("LeadsTech", size="5"),
            rx.badge("Private", color_scheme="green"),
        ),
        # Primary navigation (center).
        rx.hstack(
            nav_button("Files", "/", active_page == "files"),
            nav_button("Chat", "/chat", active_page == "chat"),
            spacing="2",
        ),
        # User + theme controls (right).
        rx.hstack(
            rx.text("Admin", color=SECONDARY_TEXT),
            rx.color_mode.button(),
            spacing="3",
        ),
        justify="between",
        align="center",
        padding_x="1.25rem",
        padding_y="0.85rem",
        border_bottom=f"1px solid {BORDER_COLOR}",
        width="100%",
        bg=PANEL_BG,
    )
