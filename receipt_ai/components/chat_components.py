import reflex as rx
from reflex_motion import motion

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
_PANEL_TINT = _mode("rgba(248,250,252,0.92)", "rgba(9,18,36,0.82)")


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
    "border": f"1px solid {BORDER_COLOR}",
    "border_radius": RADIUS_LG,
    "box_shadow": SHADOW_SM,
}


def _chat_user_bubble(m) -> rx.Component:
    """Right-aligned user pill (Technical AI agri)."""
    return motion(
        rx.hstack(
            rx.box(
                rx.text(
                    m["content"],
                    size="2",
                    color="white",
                    style={"whiteSpace": "pre-wrap"},
                ),
                max_width="min(78%, 46rem)",
                bg=_USER_BUBBLE_BG,
                padding="0.52rem 0.9rem",
                border_radius="16px",
                border_top_right_radius="6px",
                box_shadow="0 5px 14px rgba(22, 163, 74, 0.22)",
                border="1px solid rgba(255,255,255,0.18)",
            ),
            rx.center(
                rx.icon("user", size=14, color="white"),
                width="28px",
                height="28px",
                flex_shrink="0",
                border_radius="8px",
                background="linear-gradient(135deg, #22c55e 0%, #15803d 100%)",
                box_shadow="0 2px 8px rgba(34, 197, 94, 0.28)",
            ),
            justify="end",
            align="start",
            spacing="3",
            width="100%",
            padding_right="0.2rem",
        ),
        initial={"opacity": 0, "y": 8},
        animate={"opacity": 1, "y": 0},
        transition={"duration": 0.2, "ease": "easeOut"},
    )


def _chat_assistant_bubble(m) -> rx.Component:
    """Left column: gradient avatar + markdown body."""
    return motion(
        rx.hstack(
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
                rx.vstack(
                    rx.hstack(
                        rx.badge(
                            rx.cond(m.get("mode", "normal") == "reasoning", "Reasoning", "Normal"),
                            size="1",
                            variant="soft",
                            color_scheme=rx.cond(m.get("mode", "normal") == "reasoning", "green", "gray"),
                        ),
                        rx.cond(
                            m.get("is_error", "0") == "1",
                            rx.button(
                                "Retry",
                                size="1",
                                variant="soft",
                                color_scheme="orange",
                                on_click=ChatState.retry_last_turn,
                            ),
                            rx.fragment(),
                        ),
                        width="100%",
                        align="center",
                        spacing="2",
                    ),
                    rx.markdown(m["content"]),
                    rx.cond(
                        m.get("sources", []) != [],
                        rx.vstack(
                            rx.badge(
                                rx.cond(
                                    m.get("sources_count", 0) == 1,
                                    "1 source",
                                    f"{m.get('sources_count', 0)} sources",
                                ),
                                size="1",
                                variant="soft",
                                color_scheme="green",
                            ),
                            rx.text(m.get("sources_preview", ""), size="1", color=MUTED_TEXT),
                            width="100%",
                            align="start",
                            spacing="1",
                        ),
                        rx.fragment(),
                    ),
                    class_name="chat-md-prose",
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                max_width="min(82%, 50rem)",
                color=_mode("#374151", "#d1d5db"),
                bg=_mode("#f8fafc", "#0f1a2a"),
                border=f"1px solid {BORDER_COLOR}",
                border_radius="12px",
                padding="0.6rem 0.75rem",
                box_shadow=_mode("0 6px 14px rgba(15, 23, 42, 0.08)", "0 6px 14px rgba(2, 6, 23, 0.24)"),
            ),
            spacing="3",
            align="start",
            width="auto",
            max_width="100%",
        ),
        initial={"opacity": 0, "y": 8},
        animate={"opacity": 1, "y": 0},
        transition={"duration": 0.2, "ease": "easeOut"},
    )


def _chat_thinking_row() -> rx.Component:
    """Placeholder row before first streamed token (three-dot pulse)."""
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
            rx.hstack(
                rx.box(class_name="chat-thinking-dot"),
                rx.box(class_name="chat-thinking-dot"),
                rx.box(class_name="chat-thinking-dot"),
                spacing="2",
                align="center",
                class_name="chat-thinking-dots",
            ),
            padding="0.65rem 0.85rem",
            border_radius="14px",
            bg=_mode("#f8fafc", "#161b26"),
            border=f"1px solid {BORDER_COLOR}",
            min_height="44px",
            align_self="flex-start",
        ),
        spacing="3",
        align="start",
        width="100%",
    )


def _chat_streaming_row() -> rx.Component:
    """Partial assistant reply with streaming caret."""
    return motion(
        rx.hstack(
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
                rx.vstack(
                    rx.hstack(
                        rx.badge(
                            rx.cond(ChatState.streaming_mode == "reasoning", "Reasoning", "Normal"),
                            size="1",
                            variant="soft",
                            color_scheme=rx.cond(ChatState.streaming_mode == "reasoning", "green", "gray"),
                        ),
                        width="100%",
                        align="center",
                        spacing="2",
                    ),
                    rx.box(
                        rx.markdown(ChatState.streaming_text),
                        class_name="chat-md-prose chat-stream-cursor-wrap",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                max_width="min(82%, 50rem)",
                color=_mode("#374151", "#d1d5db"),
                bg=_mode("#f8fafc", "#0f1a2a"),
                border=f"1px solid {BORDER_COLOR}",
                border_radius="12px",
                padding="0.6rem 0.75rem",
                box_shadow=_mode("0 6px 14px rgba(15, 23, 42, 0.08)", "0 6px 14px rgba(2, 6, 23, 0.24)"),
            ),
            spacing="3",
            align="start",
            width="auto",
            max_width="100%",
        ),
        initial={"opacity": 0.96, "y": 4},
        animate={"opacity": 1, "y": 0},
        transition={"duration": 0.15, "ease": "easeOut"},
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
                rx.badge("DB", size="1", variant="soft", color_scheme="green"),
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
                    lambda thread: rx.hstack(
                        rx.box(
                            rx.vstack(
                                rx.text(
                                    thread["title"],
                                    size=TEXT_SIZE_SM,
                                    color=SECONDARY_TEXT,
                                    weight="medium",
                                ),
                                rx.text("Conversation thread", size="1", color=MUTED_TEXT),
                                spacing="0",
                                align="start",
                            ),
                            padding="0.42rem 0.55rem",
                            border_radius="10px",
                            width="100%",
                            cursor="pointer",
                            border=rx.cond(
                                thread["id"] == ChatState.active_conversation_id,
                                f"1px solid {border_accent}",
                                "1px solid transparent",
                            ),
                            bg=rx.cond(
                                thread["id"] == ChatState.active_conversation_id,
                                accent_soft_bg,
                                "transparent",
                            ),
                            _hover={"bg": accent_soft_bg, "border_color": border_accent, "transform": "translateX(1px)"},
                            transition="all 140ms ease",
                            on_click=ChatState.select_conversation(thread["id"]),
                        ),
                        rx.button(
                            rx.icon("trash-2", size=13),
                            size="1",
                            variant="soft",
                            color_scheme="red",
                            class_name="chat-thread-delete-btn",
                            aria_label="Delete conversation",
                            on_click=ChatState.delete_thread(thread["id"]),
                        ),
                        class_name="chat-thread-row",
                        width="100%",
                        align="center",
                        spacing="2",
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
        backdrop_filter="blur(4px)",
        bg=_PANEL_TINT,
        **_PANEL,
    )


def chat_composer() -> rx.Component:
    """Pill composer + disclaimer (TA input bar)."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.icon("sparkles", size=12, color=accent_muted_fg),
                        rx.text("Thinking", size="1", color=MUTED_TEXT, weight="medium"),
                        spacing="1",
                        align="center",
                    ),
                    rx.spacer(),
                    rx.badge(
                        rx.cond(ChatState.thinking_enabled, "Reasoning", "Normal"),
                        size="1",
                        variant="soft",
                        color_scheme=rx.cond(ChatState.thinking_enabled, "green", "gray"),
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon("brain", size=13),
                            rx.text(rx.cond(ChatState.thinking_enabled, "ON", "OFF"), size="1", weight="bold"),
                            spacing="1",
                            align="center",
                        ),
                        size="1",
                        variant=rx.cond(ChatState.thinking_enabled, "solid", "soft"),
                        color_scheme=rx.cond(ChatState.thinking_enabled, "green", "gray"),
                        on_click=ChatState.toggle_thinking_mode,
                        disabled=ChatState.rag_busy,
                        border_radius="9999px",
                        min_width="74px",
                    ),
                    width="100%",
                    align="center",
                    spacing="2",
                    padding_x="0.35rem",
                    padding_top="0.35rem",
                ),
                rx.hstack(
                    rx.text_area(
                        placeholder="Ask about your uploaded receipts…",
                        value=ChatState.draft_message,
                        on_change=ChatState.set_draft,
                        on_key_down=rx.call_script(
                            "if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); return 'send_now'; } return '';",
                            callback=ChatState.handle_composer_key_signal,
                        ),
                        size="2",
                        width="100%",
                        min_height="58px",
                        max_height="180px",
                        flex="1",
                        resize="vertical",
                        color=text_primary,
                        border="none",
                        box_shadow="none",
                        background="transparent",
                        disabled=ChatState.rag_busy,
                        padding="0.5rem 0.35rem 0.45rem 0.35rem",
                    ),
                    rx.button(
                        rx.icon("send", size=18, color="white"),
                        size="2",
                        height="42px",
                        width="42px",
                        padding="0",
                        border_radius="12px",
                        color_scheme="green",
                        on_click=ChatState.send_draft,
                        disabled=~ChatState.can_send,
                        flex_shrink="0",
                        box_shadow="0 10px 22px rgba(34, 197, 94, 0.34)",
                    ),
                    width="100%",
                    align="end",
                    spacing="2",
                    padding="0.25rem 0.45rem 0.3rem 0.45rem",
                ),
                width="100%",
                spacing="0",
            ),
            border=f"1px solid {BORDER_COLOR}",
            border_radius="16px",
            bg=_mode("rgba(249,250,251,0.96)", "rgba(11,20,39,0.88)"),
            _focus_within={
                "border_color": accent_muted_fg,
                "box_shadow": _mode(
                    "0 0 0 1px rgba(22, 163, 74, 0.25)",
                    "0 0 0 1px rgba(74, 222, 128, 0.35)",
                ),
            },
            box_shadow=_mode("0 12px 28px rgba(15, 23, 42, 0.08)", "0 16px 34px rgba(2, 6, 23, 0.42)"),
        ),
        rx.text(
            rx.cond(
                ChatState.rag_busy,
                "Receipt AI is thinking…",
                rx.cond(
                    ChatState.chat_mode == "reasoning",
                    "Reasoning mode: deeper analysis, usually slower.",
                    "Normal mode: faster replies. AI can make mistakes.",
                ),
            ),
            size="1",
            color=MUTED_TEXT,
            text_align="center",
            width="100%",
            margin_top="0.5rem",
        ),
        rx.text(
            "Enter to send - Shift+Enter for new line",
            size="1",
            color=MUTED_TEXT,
            text_align="right",
            width="100%",
            margin_top="0.15rem",
            padding_right="0.2rem",
        ),
        width="100%",
        max_width="56rem",
        margin_x="auto",
        padding_top="0.75rem",
        border_top=f"1px solid {BORDER_COLOR}",
        background=_mode(
            "linear-gradient(180deg, rgba(248,250,252,0.72) 0%, rgba(248,250,252,0.95) 100%)",
            "linear-gradient(180deg, rgba(3,7,18,0.2) 0%, rgba(3,7,18,0.66) 100%)",
        ),
        border_radius="14px",
        padding_x="0.25rem",
    )


def chat_center_panel() -> rx.Component:
    """Center: header, TA-style empty state, thread + composer."""
    return rx.box(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.icon("sparkles", size=14, color=accent_muted_fg),
                        rx.text("Chat", size="2", weight="bold", color=text_primary),
                        spacing="2",
                        align="center",
                    ),
                    rx.badge(
                        rx.cond(ChatState.thinking_enabled, "Thinking ON", "Thinking OFF"),
                        size="1",
                        variant="soft",
                        color_scheme=rx.cond(ChatState.thinking_enabled, "green", "gray"),
                    ),
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
                                    ChatState.streaming_text != "",
                                    _chat_streaming_row(),
                                    rx.cond(
                                        ChatState.rag_busy,
                                        _chat_thinking_row(),
                                        rx.fragment(),
                                    ),
                                ),
                                spacing="3",
                                width="100%",
                                align="stretch",
                            ),
                            width="100%",
                            max_width="56rem",
                            margin_x="auto",
                            padding_x="0.25rem",
                        ),
                        rx.center(
                            motion(
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
                                initial={"opacity": 0, "y": 10},
                                animate={"opacity": 1, "y": 0},
                                transition={"duration": 0.25, "ease": "easeOut"},
                            ),
                            width="100%",
                            min_height="220px",
                        ),
                    ),
                    width="100%",
                    flex="1",
                    min_height="180px",
                    max_height="calc(100vh - 220px)",
                    id="chat-thread-scroll",
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
            bg=_PANEL_TINT,
            backdrop_filter="blur(4px)",
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
                rx.box(
                    rx.text("Send a message to see recents here.", size=TEXT_SIZE_SM, color=MUTED_TEXT),
                    width="100%",
                    padding="0.6rem",
                    border=f"1px dashed {BORDER_COLOR}",
                    border_radius="10px",
                    bg=_mode("rgba(248,250,252,0.6)", "rgba(15,23,42,0.5)"),
                ),
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        padding="0.65rem 0.75rem",
        height="100%",
        backdrop_filter="blur(4px)",
        bg=_PANEL_TINT,
        **_PANEL,
    )
