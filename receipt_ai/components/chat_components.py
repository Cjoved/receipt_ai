import reflex as rx

from receipt_ai.components.ui.buttons import primary_action_button
from receipt_ai.core.constants import BORDER_COLOR, SECONDARY_TEXT, SUBTLE_BG
from receipt_ai.features.chat.service import list_chat_payload

CHATS = list_chat_payload()


def chat_history() -> rx.Component:
    """Left sidebar: chat history list + new chat action."""
    return rx.vstack(
        # Header + primary action.
        rx.heading("Chat", size="4"),
        primary_action_button("+ New Chat", width="100%"),
        # Chat history items.
        rx.vstack(
            *[
                rx.box(
                    rx.text(msg, size="2", color=SECONDARY_TEXT),
                    padding="0.5rem 0.65rem",
                    border_radius="8px",
                    bg=SUBTLE_BG,
                    width="100%",
                )
                for msg in CHATS
            ],
            spacing="2",
            width="100%",
            align="start",
        ),
        spacing="3",
        width="100%",
        align="start",
    )


def chat_center_panel() -> rx.Component:
    """Center panel: empty state for chat."""
    return rx.center(
        rx.vstack(
            rx.box(height="44px", width="44px", bg="#22c55e", border_radius="10px"),
            rx.heading("How can I help you today?", size="5"),
            rx.text(
                "Ask about your uploaded documents - crops, pests, diseases, and more.",
                color=SECONDARY_TEXT,
                text_align="center",
                max_width="420px",
            ),
            spacing="3",
        ),
        min_height="260px",
        width="100%",
    )


def recent_chats_panel() -> rx.Component:
    """Right panel: additional recent chat shortcuts (placeholder)."""
    return rx.vstack(
        rx.heading("Recent Chats", size="5"),
        rx.vstack(
            *[
                rx.box(
                    rx.text(msg, size="2", color=SECONDARY_TEXT),
                    padding="0.6rem 0.75rem",
                    border_radius="10px",
                    bg=SUBTLE_BG,
                    border=f"1px solid {BORDER_COLOR}",
                    width="100%",
                )
                for msg in CHATS
            ],
            spacing="2",
            width="100%",
            align="start",
        ),
        spacing="3",
        width="100%",
        align="start",
    )
