import reflex as rx

from receipt_ai.components.ui.buttons import icon_button
from receipt_ai.components.ui.modals import confirm_modal
from receipt_ai.core.constants import (
    BORDER_COLOR,
    ICON_SIZE_SM,
    MUTED_TEXT,
    PANEL_BG,
    SECONDARY_TEXT,
    TEXT_SIZE_MD,
    TEXT_SIZE_SM,
)
from receipt_ai.core.theme.tokens import (
    RADIUS_LG,
    SHADOW_SM,
    accent_muted_fg,
    accent_soft_bg,
    border_accent,
    text_primary,
    theme_pair as _mode,
)
from receipt_ai.features.chat.state import ChatState

_USER_BUBBLE_BG = _mode("#16a34a", "#22c55e")


def new_chat_confirm_modal() -> rx.Component:
    return confirm_modal(
        open_state=ChatState.show_new_chat_confirm,
        title="Start a new chat?",
        body=rx.text(
            "This clears the current conversation from the screen. Continue?",
            size="2",
            color=rx.color("gray", 11),
        ),
        confirm_label="New chat",
        on_confirm=ChatState.confirm_new_chat,
        on_cancel=ChatState.cancel_new_chat_confirm,
        confirm_color_scheme="green",
    )


_PANEL = {
    "width": "100%",
    "bg": PANEL_BG,
    "border": f"1px solid {BORDER_COLOR}",
    "border_radius": RADIUS_LG,
    "box_shadow": SHADOW_SM,
}


def _chat_user_bubble(m) -> rx.Component:
    """Right-aligned user pill (Technical AI agri)."""
    return rx.box(
        rx.text(
            m["content"],
            size="2",
            color="white",
            style={"whiteSpace": "pre-wrap"},
        ),
        max_width="75%",
        align_self="flex-end",
        bg=_USER_BUBBLE_BG,
        padding="0.55rem 0.95rem",
        border_radius="16px",
        border_top_right_radius="6px",
        box_shadow="0 1px 2px rgba(0,0,0,0.06)",
    )


def _chat_assistant_bubble(m) -> rx.Component:
    """Left column: gradient avatar + markdown body."""
    return rx.hstack(
        rx.center(
            rx.icon("leaf", size=16, color="white"),
            width="28px",
            height="28px",
            flex_shrink="0",
            border_radius="8px",
            background="linear-gradient(135deg, #22c55e 0%, #15803d 100%)",
            box_shadow="0 2px 8px rgba(34, 197, 94, 0.28)",
        ),
        rx.box(
            rx.markdown(m["content"]),
            class_name="chat-md-prose",
            max_width="min(75%, 42rem)",
            color=_mode("#374151", "#d1d5db"),
            bg=_mode("#f8fafc", "#0b172d"),
            border=f"1px solid {BORDER_COLOR}",
            border_radius="14px",
            padding="0.6rem 0.75rem",
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def chat_history() -> rx.Component:
    """Left rail: thread list + new chat (TA ~260px feel via shell max-width)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("message-square", size=16, color=accent_muted_fg),
                    rx.heading("History", size="4", weight="bold", color=text_primary),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                icon_button("rotate-cw", "Refresh threads", on_click=ChatState.load_history),
                width="100%",
                align="center",
            ),
            rx.button(
                rx.hstack(rx.icon("plus", size=16), rx.text("New chat"), spacing="2", align="center"),
                width="100%",
                size="2",
                color_scheme="green",
                variant="solid",
                on_click=ChatState.open_new_chat_confirm,
            ),
            new_chat_confirm_modal(),
            rx.vstack(
                rx.foreach(
                    ChatState.sidebar_threads,
                    lambda title: rx.box(
                        rx.text(title, size=TEXT_SIZE_MD, color=SECONDARY_TEXT),
                        padding="0.5rem 0.65rem",
                        border_radius="12px",
                        width="100%",
                        cursor="pointer",
                        border="1px solid transparent",
                        _hover={"bg": accent_soft_bg, "border_color": border_accent},
                    ),
                ),
                spacing="1",
                width="100%",
                align="start",
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        padding="0.65rem 0.75rem",
        **_PANEL,
    )


def chat_composer() -> rx.Component:
    """Pill composer + disclaimer (TA input bar)."""
    return rx.box(
        rx.box(
            rx.hstack(
                rx.text_area(
                    placeholder="Message…",
                    value=ChatState.draft_message,
                    on_change=ChatState.set_draft,
                    size="2",
                    width="100%",
                    min_height="44px",
                    max_height="160px",
                    flex="1",
                    resize="vertical",
                    color=text_primary,
                    border="none",
                    box_shadow="none",
                    background="transparent",
                    disabled=ChatState.rag_busy,
                ),
                rx.button(
                    rx.icon("send", size=18, color="white"),
                    size="2",
                    height="36px",
                    width="36px",
                    padding="0",
                    border_radius="10px",
                    color_scheme="green",
                    on_click=ChatState.send_draft,
                    disabled=~ChatState.can_send,
                    flex_shrink="0",
                ),
                width="100%",
                align="end",
                spacing="2",
                padding="0.2rem 0.35rem",
            ),
            border=f"1px solid {BORDER_COLOR}",
            border_radius="16px",
            bg=_mode("rgba(249,250,251,0.95)", "rgba(15,23,42,0.6)"),
            _focus_within={
                "border_color": accent_muted_fg,
                "box_shadow": _mode(
                    "0 0 0 1px rgba(22, 163, 74, 0.25)",
                    "0 0 0 1px rgba(74, 222, 128, 0.35)",
                ),
            },
        ),
        rx.text(
            rx.cond(
                ChatState.rag_busy,
                "Receipt AI is thinking…",
                "AI can make mistakes. Verify important information.",
            ),
            size="1",
            color=MUTED_TEXT,
            text_align="center",
            width="100%",
            margin_top="0.45rem",
        ),
        width="100%",
        max_width="48rem",
        margin_x="auto",
        padding_top="0.75rem",
        border_top=f"1px solid {BORDER_COLOR}",
    )


def chat_center_panel() -> rx.Component:
    """Center: header, TA-style empty state, thread + composer."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text("Chat", size="2", weight="bold", color=text_primary),
                    rx.spacer(),
                    width="100%",
                    align="center",
                    padding_bottom="0.5rem",
                    border_bottom=f"1px solid {BORDER_COLOR}",
                    class_name="chat-thread-header",
                ),
                rx.box(
                    rx.cond(
                        ChatState.has_messages,
                        rx.box(
                            rx.vstack(
                                rx.foreach(
                                    ChatState.messages,
                                    lambda m: rx.cond(
                                        m["role"] == "user",
                                        _chat_user_bubble(m),
                                        _chat_assistant_bubble(m),
                                    ),
                                ),
                                rx.cond(
                                    ChatState.rag_busy,
                                    rx.hstack(
                                        rx.spinner(size="2", color=accent_muted_fg),
                                        rx.text("Analyzing your documents…", size="2", color=SECONDARY_TEXT),
                                        spacing="2",
                                        align="center",
                                        width="100%",
                                    ),
                                ),
                                spacing="4",
                                width="100%",
                                align="stretch",
                            ),
                            width="100%",
                            max_width="48rem",
                            margin_x="auto",
                            padding_x="0.5rem",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.center(
                                    rx.icon("leaf", size=28, color="white"),
                                    width="56px",
                                    height="56px",
                                    border_radius="16px",
                                    background="linear-gradient(135deg, #22c55e 0%, #15803d 100%)",
                                    box_shadow="0 10px 28px rgba(34, 197, 94, 0.35)",
                                ),
                                rx.heading(
                                    "How can I help you today?",
                                    size="5",
                                    weight="bold",
                                    color=text_primary,
                                ),
                                rx.text(
                                    "Ask about your uploaded documents — crops, pests, diseases, receipts, and more.",
                                    color=SECONDARY_TEXT,
                                    text_align="center",
                                    max_width="420px",
                                    size=TEXT_SIZE_SM,
                                    line_height="1.5",
                                ),
                                spacing="3",
                                align="center",
                            ),
                            width="100%",
                            min_height="220px",
                        ),
                    ),
                    width="100%",
                    flex="1",
                    min_height="180px",
                    max_height="calc(100vh - 220px)",
                    overflow_y="auto",
                    padding_y="0.5rem",
                    padding_right="0.25rem",
                ),
                chat_composer(),
                spacing="0",
                width="100%",
                align="stretch",
                min_height="0",
                flex="1",
            ),
            height="100%",
            display="flex",
            flex_direction="column",
            padding="0.75rem",
            flex="1",
            min_height="0",
            **_PANEL,
        ),
        width="100%",
        height="100%",
        min_height="0",
        display="flex",
        flex_direction="column",
    )


def recent_chats_panel() -> rx.Component:
    """Session recents (Technical AI–style snippet list)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("history", size=16, color=accent_muted_fg),
                rx.heading("Recent", size="4", weight="bold", color=text_primary),
                spacing="2",
                align="center",
            ),
            rx.cond(
                ChatState.has_messages,
                rx.vstack(
                    rx.foreach(
                        ChatState.recent_messages,
                        lambda msg: rx.box(
                            rx.text(msg, size=TEXT_SIZE_SM, color=SECONDARY_TEXT),
                            padding="0.5rem 0.6rem",
                            border_radius="10px",
                            bg=accent_soft_bg,
                            border=f"1px solid {BORDER_COLOR}",
                            width="100%",
                        ),
                    ),
                    spacing="2",
                    width="100%",
                    align="start",
                ),
                rx.text("Send a message to see recents here.", size=TEXT_SIZE_SM, color=MUTED_TEXT),
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        padding="0.65rem 0.75rem",
        height="100%",
        **_PANEL,
    )
