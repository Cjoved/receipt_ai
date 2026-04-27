import reflex as rx
from reflex_motion import motion

from receipt_ai.components.ui.buttons import icon_button
from receipt_ai.core.upload_constants import CHAT_UPLOAD_ACCEPT, CHAT_UPLOAD_ZONE_ID
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
from receipt_ai.features.auth.state import AuthState

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


def delete_chat_confirm_modal() -> rx.Component:
    return confirm_modal(
        open_state=ChatState.show_delete_chat_confirm,
        title="Delete this conversation?",
        body=rx.text(
            "This will permanently remove the selected thread and its messages.",
            size="2",
            color=rx.color("gray", 11),
        ),
        confirm_label="Delete",
        on_confirm=ChatState.confirm_delete_thread,
        on_cancel=ChatState.cancel_delete_thread,
        confirm_color_scheme="red",
    )


def source_selector_modal() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Open source"),
            rx.alert_dialog.description(
                rx.vstack(
                    rx.text("Select a source file to open.", size="2", color=rx.color("gray", 11)),
                    rx.vstack(
                        rx.foreach(
                            ChatState.source_selector_items,
                            lambda source, idx: rx.button(
                                rx.hstack(
                                    rx.badge(source.get("source_index", 0), size="1", variant="soft", color_scheme="gray"),
                                    rx.text(source.get("source_name", "source"), size="2"),
                                    rx.spacer(),
                                    rx.badge(source.get("chunk_index", 0), size="1", variant="soft"),
                                    spacing="2",
                                    align="center",
                                    width="100%",
                                ),
                                variant="soft",
                                width="100%",
                                justify="start",
                                on_click=ChatState.open_source_selector_item(idx),
                            ),
                        ),
                        width="100%",
                        spacing="2",
                        align="start",
                    ),
                    width="100%",
                    spacing="2",
                    align="start",
                )
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button("Close", variant="outline", on_click=ChatState.close_source_selector),
                ),
                justify="end",
                width="100%",
            ),
        ),
        open=ChatState.show_source_selector,
    )


_PANEL = {
    "width": "100%",
    "border": f"1px solid {BORDER_COLOR}",
    "border_radius": RADIUS_LG,
    "box_shadow": SHADOW_SM,
}


def _chat_user_bubble(m, idx) -> rx.Component:
    """Right-aligned user pill (Technical AI agri)."""
    return motion(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.vstack(
                    rx.cond(
                        m.get("attachment_preview_url_1", "") != "",
                        rx.flex(
                            rx.image(
                                src=m.get("attachment_preview_url_1", ""),
                                width="72px",
                                height="72px",
                                object_fit="cover",
                                border_radius="8px",
                                border="1px solid rgba(255,255,255,0.35)",
                                cursor="pointer",
                                on_click=ChatState.open_message_image_preview_group(
                                    0,
                                    m.get("attachment_name_1", ""),
                                    m.get("attachment_preview_url_1", ""),
                                    m.get("attachment_name_2", ""),
                                    m.get("attachment_preview_url_2", ""),
                                    m.get("attachment_name_3", ""),
                                    m.get("attachment_preview_url_3", ""),
                                ),
                            ),
                            rx.cond(
                                m.get("attachment_preview_url_2", "") != "",
                                rx.image(
                                    src=m.get("attachment_preview_url_2", ""),
                                    width="72px",
                                    height="72px",
                                    object_fit="cover",
                                    border_radius="8px",
                                    border="1px solid rgba(255,255,255,0.35)",
                                    cursor="pointer",
                                    on_click=ChatState.open_message_image_preview_group(
                                        1,
                                        m.get("attachment_name_1", ""),
                                        m.get("attachment_preview_url_1", ""),
                                        m.get("attachment_name_2", ""),
                                        m.get("attachment_preview_url_2", ""),
                                        m.get("attachment_name_3", ""),
                                        m.get("attachment_preview_url_3", ""),
                                    ),
                                ),
                                rx.fragment(),
                            ),
                            rx.cond(
                                m.get("attachment_preview_url_3", "") != "",
                                rx.image(
                                    src=m.get("attachment_preview_url_3", ""),
                                    width="72px",
                                    height="72px",
                                    object_fit="cover",
                                    border_radius="8px",
                                    border="1px solid rgba(255,255,255,0.35)",
                                    cursor="pointer",
                                    on_click=ChatState.open_message_image_preview_group(
                                        2,
                                        m.get("attachment_name_1", ""),
                                        m.get("attachment_preview_url_1", ""),
                                        m.get("attachment_name_2", ""),
                                        m.get("attachment_preview_url_2", ""),
                                        m.get("attachment_name_3", ""),
                                        m.get("attachment_preview_url_3", ""),
                                    ),
                                ),
                                rx.fragment(),
                            ),
                            gap="2",
                            align="start",
                            wrap="wrap",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        (ChatState.editing_message_id == m.get("id", "")) & (ChatState.editing_message_index == idx),
                        rx.form(
                            rx.vstack(
                                rx.text_area(
                                    name="inline_edit",
                                    value=ChatState.inline_edit_text,
                                    on_change=ChatState.set_inline_edit_text,
                                    enter_key_submit=True,
                                    auto_height=True,
                                    rows="2",
                                    placeholder="Edit your message...",
                                    width="100%",
                                    min_height="68px",
                                    max_height="220px",
                                    resize="vertical",
                                    size="2",
                                ),
                                rx.hstack(
                                    rx.button(
                                        "Save",
                                        type="submit",
                                        size="1",
                                        color_scheme="green",
                                        variant="solid",
                                    ),
                                    rx.button(
                                        "Cancel",
                                        type="button",
                                        size="1",
                                        variant="soft",
                                        color_scheme="gray",
                                        on_click=ChatState.cancel_inline_edit,
                                    ),
                                    rx.spacer(),
                                    rx.text("Enter to save - Shift+Enter newline", size="1", color="white"),
                                    width="100%",
                                    align="center",
                                    spacing="2",
                                ),
                                width="100%",
                                spacing="2",
                            ),
                            on_submit=ChatState.submit_inline_edit_form,
                            reset_on_submit=False,
                            width="100%",
                        ),
                        rx.text(
                            m["content"],
                            size="2",
                            color="white",
                            style={"whiteSpace": "pre-wrap"},
                        ),
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                    ),
                    max_width="min(90%, 64rem)",
                    bg=_USER_BUBBLE_BG,
                    padding="0.52rem 0.9rem",
                    border_radius="16px",
                    border_top_right_radius="6px",
                    box_shadow="0 5px 14px rgba(22, 163, 74, 0.22)",
                    border="1px solid rgba(255,255,255,0.18)",
                    class_name="chat-user-bubble",
                ),
                rx.center(
                    rx.icon("user", size=14, color="white"),
                    width="28px",
                    height="28px",
                    flex_shrink="0",
                    border_radius="8px",
                    background=_mode("linear-gradient(135deg, #14b8a6 0%, #0f766e 100%)", "linear-gradient(135deg, #0f766e 0%, #115e59 100%)"),
                    box_shadow="0 2px 8px rgba(20, 184, 166, 0.3)",
                ),
                justify="end",
                align="start",
                spacing="3",
                width="auto",
                padding_right="0.2rem",
            ),
            rx.hstack(
                rx.button(
                    rx.icon(
                        rx.cond(
                            (ChatState.message_action_role == "user") & (ChatState.message_action_index == idx),
                            "check",
                            "copy",
                        ),
                        size=14,
                        color=_mode("#0f172a", "#f8fafc"),
                    ),
                    size="1",
                    variant=rx.cond(
                        (ChatState.message_action_role == "user") & (ChatState.message_action_index == idx),
                        "solid",
                        "soft",
                    ),
                    color_scheme=rx.cond(
                        (ChatState.message_action_role == "user") & (ChatState.message_action_index == idx),
                        "green",
                        "gray",
                    ),
                    on_click=ChatState.copy_message_action(m["content"], "user", idx),
                    aria_label="Copy message",
                    title="Copy",
                ),
                rx.button(
                    rx.icon("pencil", size=14, color=_mode("#0f172a", "#f8fafc")),
                    size="1",
                    variant="soft",
                    color_scheme="gray",
                    on_click=ChatState.edit_message_to_draft(m["content"], m.get("id", ""), idx),
                    aria_label="Edit message",
                    title="Edit",
                ),
                rx.button(
                    rx.icon("refresh-cw", size=14, color=_mode("#0f172a", "#f8fafc")),
                    size="1",
                    variant="soft",
                    color_scheme="gray",
                    on_click=ChatState.resend_message_from_bubble(m["content"], m.get("id", ""), idx),
                    aria_label="Resend message",
                    title="Resend",
                ),
                class_name="chat-bubble-actions",
                spacing="1",
                justify="end",
                width="100%",
            ),
            width="100%",
            align="end",
            spacing="0",
            class_name="chat-user-row",
        ),
        initial={"opacity": 0, "y": 8},
        animate={"opacity": 1, "y": 0},
        transition={"duration": 0.2, "ease": "easeOut"},
    )


def _chat_assistant_bubble(m, idx) -> rx.Component:
    """Left column: gradient avatar + markdown body."""
    return motion(
        rx.vstack(
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
                            rx.cond(
                                idx == (ChatState.message_count - 1),
                                rx.cond(
                                    (ChatState.regenerating_message_id == m.get("id", "")) & ChatState.rag_busy,
                                    rx.button(
                                        rx.icon("rotate-cw", size=13, class_name="chat-regen-spin"),
                                        size="1",
                                        variant="soft",
                                        color_scheme="green",
                                        disabled=True,
                                        aria_label="Regenerating response",
                                        title="Regenerating",
                                    ),
                                    rx.button(
                                        rx.icon("rotate-cw", size=13),
                                        size="1",
                                        variant="soft",
                                        color_scheme="green",
                                        on_click=ChatState.regenerate_assistant_message(m.get("id", ""), idx),
                                        aria_label="Regenerate response",
                                        title="Regenerate",
                                    ),
                                ),
                                rx.fragment(),
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.spacer(),
                        rx.cond(
                            m.get("has_multiple_versions", "0") == "1",
                            rx.hstack(
                                rx.button(
                                    rx.icon("chevron-left", size=12),
                                    size="1",
                                    variant="soft",
                                    on_click=ChatState.show_prev_response_version(m.get("id", "")),
                                    disabled=m.get("has_prev_version", "0") == "0",
                                    aria_label="Previous response version",
                                ),
                                rx.badge(
                                    m.get("version_label", "1"),
                                    size="1",
                                    variant="soft",
                                    color_scheme="gray",
                                ),
                                rx.button(
                                    rx.icon("chevron-right", size=12),
                                    size="1",
                                    variant="soft",
                                    on_click=ChatState.show_next_response_version(m.get("id", "")),
                                    disabled=m.get("has_next_version", "0") == "0",
                                    aria_label="Next response version",
                                ),
                                spacing="1",
                                align="center",
                            ),
                            rx.fragment(),
                        ),
                        width="100%",
                        align="center",
                    ),
                    rx.markdown(m["content"]),
                    rx.cond(
                        m.get("sources", []) != [],
                        rx.vstack(
                            rx.badge(
                                rx.cond(
                                    m.get("sources_file_count", 0) == 0,
                                    rx.cond(
                                        m.get("sources_count", 0) == 1,
                                        "1 source",
                                        f"{m.get('sources_count', 0)} sources",
                                    ),
                                    rx.cond(
                                        m.get("sources_file_count", 0) == 1,
                                        f"1 file, {m.get('sources_chunk_count', m.get('sources_count', 0))} chunks",
                                        f"{m.get('sources_file_count', 0)} files, {m.get('sources_chunk_count', m.get('sources_count', 0))} chunks",
                                    ),
                                ),
                                size="1",
                                variant="soft",
                                color_scheme="green",
                            ),
                            rx.text(
                                m.get("sources_lines", m.get("sources_preview", "")),
                                size="1",
                                color=SECONDARY_TEXT,
                                white_space="pre-wrap",
                                class_name="chat-source-line",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.button(
                                    rx.hstack(
                                        rx.icon("external-link", size=12),
                                        rx.text("Open", size="1"),
                                        spacing="1",
                                        align="center",
                                    ),
                                    size="1",
                                    variant="soft",
                                    on_click=ChatState.open_message_source(m.get("id", "")),
                                ),
                                rx.button(
                                    rx.hstack(
                                        rx.icon("quote", size=12),
                                        rx.text("Citation", size="1"),
                                        spacing="1",
                                        align="center",
                                    ),
                                    size="1",
                                    variant="soft",
                                    on_click=ChatState.copy_message_citation(m.get("id", ""), "assistant", idx),
                                ),
                                spacing="1",
                                wrap="wrap",
                            ),
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
                    width="auto",
                    max_width="min(94%, 72rem)",
                    color=_mode("#374151", "#d1d5db"),
                    bg=_mode("#f8fafc", "#0f1a2a"),
                    border=f"1px solid {BORDER_COLOR}",
                    border_radius="12px",
                    padding="0.6rem 0.75rem",
                    box_shadow=_mode("0 6px 14px rgba(15, 23, 42, 0.08)", "0 6px 14px rgba(2, 6, 23, 0.24)"),
                    class_name="chat-assistant-bubble",
                ),
                spacing="3",
                align="start",
                width="auto",
                max_width="fit-content",
            ),
            rx.hstack(
                rx.button(
                    rx.icon(
                        rx.cond(
                            (ChatState.message_action_role == "assistant") & (ChatState.message_action_index == idx),
                            "check",
                            "copy",
                        ),
                        size=14,
                        color=_mode("#0f172a", "#f8fafc"),
                    ),
                    size="1",
                    variant=rx.cond(
                        (ChatState.message_action_role == "assistant") & (ChatState.message_action_index == idx),
                        "solid",
                        "soft",
                    ),
                    color_scheme=rx.cond(
                        (ChatState.message_action_role == "assistant") & (ChatState.message_action_index == idx),
                        "green",
                        "gray",
                    ),
                    on_click=ChatState.copy_message_action(m["content"], "assistant", idx),
                    aria_label="Copy assistant message",
                    title="Copy",
                ),
                rx.button(
                    rx.icon("file-text", size=14, color=_mode("#0f172a", "#f8fafc")),
                    size="1",
                    variant="soft",
                    color_scheme="gray",
                    on_click=ChatState.copy_markdown_stub(m["content"], "assistant", idx),
                    aria_label="Copy markdown",
                    title="Copy markdown",
                ),
                rx.button(
                    rx.icon("thumbs-up", size=14, color=_mode("#0f172a", "#f8fafc")),
                    size="1",
                    variant="soft",
                    color_scheme=rx.cond(m.get("feedback_vote", "") == "up", "green", "gray"),
                    on_click=ChatState.set_message_feedback(m.get("id", ""), "up"),
                    aria_label="Helpful response",
                    title="Helpful",
                ),
                rx.button(
                    rx.icon("thumbs-down", size=14, color=_mode("#0f172a", "#f8fafc")),
                    size="1",
                    variant="soft",
                    color_scheme=rx.cond(m.get("feedback_vote", "") == "down", "orange", "gray"),
                    on_click=ChatState.set_message_feedback(m.get("id", ""), "down"),
                    aria_label="Not helpful response",
                    title="Not helpful",
                ),
                class_name="chat-bubble-actions",
                spacing="1",
                justify="start",
                width="100%",
            ),
            width="100%",
            align="start",
            spacing="0",
            class_name="chat-assistant-row",
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
                width="auto",
                max_width="min(94%, 72rem)",
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
                rx.button(
                    rx.icon(
                        "rotate-cw",
                        size=ICON_SIZE_SM,
                        class_name=rx.cond(ChatState.history_refreshing, "chat-refresh-spin", ""),
                    ),
                    variant="ghost",
                    size="1",
                    on_click=ChatState.refresh_threads,
                    disabled=ChatState.history_refreshing,
                    title="Refresh threads",
                    min_width="28px",
                    min_height="28px",
                    border="1px solid transparent",
                    border_radius="8px",
                ),
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
            delete_chat_confirm_modal(),
            source_selector_modal(),
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
                                    class_name="chat-thread-title",
                                    title=thread["title"],
                                ),
                                rx.text("Conversation thread", size="1", color=MUTED_TEXT),
                                spacing="0",
                                align="start",
                            ),
                            padding="0.42rem 0.55rem",
                            padding_right="2.2rem",
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
                            on_click=ChatState.request_delete_thread(thread["id"]),
                            position="absolute",
                            right="0.4rem",
                            top="50%",
                            transform="translateY(-50%)",
                        ),
                        class_name="chat-thread-row",
                        width="100%",
                        align="center",
                        spacing="2",
                        position="relative",
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
        rx.cond(
            ChatState.history_refreshing,
            rx.box(
                rx.hstack(
                    rx.icon("loader-circle", size=16, class_name="chat-refresh-spin"),
                    rx.text("Refreshing...", size="1", color=MUTED_TEXT),
                    spacing="2",
                    align="center",
                ),
                position="absolute",
                inset="0",
                display="flex",
                align_items="center",
                justify_content="center",
                bg=_mode("rgba(248,250,252,0.38)", "rgba(3,7,18,0.45)"),
                backdrop_filter="blur(2px)",
                border_radius=RADIUS_LG,
                z_index="2",
            ),
            rx.fragment(),
        ),
        padding="0.65rem 0.75rem",
        backdrop_filter="blur(4px)",
        bg=_PANEL_TINT,
        position="relative",
        filter=rx.cond(ChatState.history_refreshing, "blur(0.4px)", "none"),
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
                rx.cond(
                    AuthState.is_standard_user & AuthState.can_chat_image_upload,
                    rx.vstack(
                        rx.cond(
                            ChatState.chat_upload_previews != [],
                            rx.hstack(
                                rx.foreach(
                                    ChatState.chat_upload_previews,
                                    lambda item: rx.vstack(
                                        rx.box(
                                            rx.image(
                                                src=item["preview_url"],
                                                width="74px",
                                                height="74px",
                                                object_fit="cover",
                                                border_radius="8px",
                                                border=f"1px solid {BORDER_COLOR}",
                                                cursor="pointer",
                                                on_click=ChatState.open_chat_image_preview(item["name"]),
                                            ),
                                            rx.button(
                                                rx.icon("x", size=12),
                                                size="1",
                                                variant="solid",
                                                color_scheme="gray",
                                                on_click=ChatState.remove_chat_upload_preview(item["name"]),
                                                title=f"Remove {item['name']}",
                                                aria_label=f"Remove {item['name']}",
                                                position="absolute",
                                                top="4px",
                                                right="4px",
                                                min_width="20px",
                                                min_height="20px",
                                                width="20px",
                                                height="20px",
                                                padding="0",
                                                border_radius="9999px",
                                            ),
                                            position="relative",
                                        ),
                                        rx.text(
                                            item["name"],
                                            size="1",
                                            color=MUTED_TEXT,
                                            max_width="80px",
                                            style={"lineHeight": "1.1"},
                                        ),
                                        spacing="1",
                                        align="start",
                                    ),
                                ),
                                rx.spacer(),
                                rx.button(
                                    "Clear",
                                    size="1",
                                    variant="ghost",
                                    on_click=ChatState.clear_chat_upload_selection,
                                ),
                                width="100%",
                                spacing="2",
                                align="start",
                            ),
                            rx.fragment(),
                        ),
                        rx.cond(
                            (ChatState.chat_upload_previews == []) & (rx.selected_files(CHAT_UPLOAD_ZONE_ID) != []),
                            rx.hstack(
                                rx.foreach(
                                    rx.selected_files(CHAT_UPLOAD_ZONE_ID),
                                    lambda fname: rx.text(fname, size="1", color=MUTED_TEXT),
                                ),
                                width="100%",
                                spacing="2",
                                align="center",
                            ),
                            rx.fragment(),
                        ),
                        rx.cond(
                            ChatState.chat_upload_error != "",
                            rx.text(ChatState.chat_upload_error, size="1", color="red"),
                            rx.fragment(),
                        ),
                        rx.text(
                            "Attach up to 3 images (jpg, png, webp, gif, bmp). You can send with text or image-only.",
                            size="1",
                            color=MUTED_TEXT,
                        ),
                        width="100%",
                        spacing="1",
                        padding_x="0.45rem",
                        padding_bottom="0.12rem",
                    ),
                ),
                rx.form(
                    rx.hstack(
                    rx.cond(
                        AuthState.is_standard_user & AuthState.can_chat_image_upload,
                        rx.box(
                            rx.upload(
                                rx.button(
                                    rx.icon("paperclip", size=16),
                                    size="2",
                                    variant="soft",
                                    title="Attach image",
                                    disabled=ChatState.rag_busy,
                                    width="38px",
                                    height="38px",
                                    min_width="38px",
                                    padding="0",
                                    border_radius="10px",
                                ),
                                id=CHAT_UPLOAD_ZONE_ID,
                                max_files=3,
                                accept=CHAT_UPLOAD_ACCEPT,
                                on_drop=ChatState.cache_chat_upload_previews,
                                width="38px",
                                height="38px",
                                min_height="38px",
                                border="none",
                                padding="0",
                                margin="0",
                                background="transparent",
                            ),
                            width="38px",
                            height="38px",
                            flex_shrink="0",
                        ),
                    ),
                    rx.text_area(
                        name="chat_message",
                        placeholder="Ask about your uploaded receipts…",
                        value=ChatState.draft_message,
                        on_change=ChatState.set_draft,
                        on_key_up=rx.call_script(
                            "if (event.key === 'Enter' && event.shiftKey) {"
                            "  setTimeout(() => {"
                            "    const el = document.getElementById('chat-thread-scroll');"
                            "    if (el) { el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }); }"
                            "  }, 0);"
                            "}"
                        ),
                        enter_key_submit=True,
                        auto_height=True,
                        rows="1",
                        size="2",
                        width="100%",
                        min_height="58px",
                        max_height="180px",
                        flex="1",
                        resize="none",
                        color=text_primary,
                        border="none",
                        box_shadow="none",
                        background="transparent",
                        disabled=ChatState.rag_busy,
                        padding="0.5rem 0.35rem 0.45rem 0.35rem",
                    ),
                    rx.cond(
                        ChatState.rag_busy,
                        rx.button(
                            rx.icon("square", size=16, color="white"),
                            type="button",
                            size="2",
                            height="42px",
                            width="42px",
                            padding="0",
                            border_radius="12px",
                            color_scheme="orange",
                            on_click=ChatState.request_stop_generation,
                            flex_shrink="0",
                            box_shadow="0 10px 22px rgba(249, 115, 22, 0.28)",
                            aria_label="Stop generating",
                            title="Stop",
                        ),
                        rx.button(
                            rx.icon("send", size=18, color="white"),
                            type="submit",
                            size="2",
                            height="42px",
                            width="42px",
                            padding="0",
                            border_radius="12px",
                            color_scheme="green",
                            disabled=~ChatState.can_send,
                            flex_shrink="0",
                            box_shadow="0 10px 22px rgba(34, 197, 94, 0.34)",
                            aria_label="Send message",
                            title="Send",
                        ),
                    ),
                    width="100%",
                    align="end",
                    spacing="2",
                    padding="0.25rem 0.45rem 0.3rem 0.45rem",
                    ),
                    on_submit=ChatState.submit_chat_form,
                    reset_on_submit=False,
                    width="100%",
                ),
                width="100%",
                spacing="0",
            ),
            rx.cond(
                ChatState.show_chat_image_preview,
                rx.box(
                    rx.box(
                        rx.hstack(
                            rx.text(
                                ChatState.chat_preview_name,
                                weight="bold",
                                color=text_primary,
                                size="2",
                            ),
                            rx.spacer(),
                            rx.button(
                                rx.icon("chevron-left", size=16),
                                size="1",
                                variant="soft",
                                on_click=ChatState.preview_prev_image,
                                disabled=~ChatState.chat_preview_has_prev,
                                aria_label="Previous image",
                            ),
                            rx.button(
                                rx.icon("chevron-right", size=16),
                                size="1",
                                variant="soft",
                                on_click=ChatState.preview_next_image,
                                disabled=~ChatState.chat_preview_has_next,
                                aria_label="Next image",
                            ),
                            rx.button(
                                rx.icon("x", size=16),
                                size="1",
                                variant="soft",
                                on_click=ChatState.close_chat_image_preview,
                                aria_label="Close preview",
                            ),
                            width="100%",
                            align="center",
                        ),
                        rx.image(
                            src=ChatState.chat_preview_url,
                            width="min(84vw, 980px)",
                            max_height="80vh",
                            object_fit="contain",
                            border_radius="12px",
                            border=f"1px solid {BORDER_COLOR}",
                            bg=rx.color("gray", 1),
                        ),
                        spacing="2",
                        width="min(86vw, 980px)",
                        on_click=rx.call_script("event.stopPropagation()"),
                    ),
                    position="fixed",
                    inset="0",
                    z_index="10001",
                    background="rgba(2, 6, 23, 0.80)",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    padding="1rem",
                    id="chat-image-preview-overlay",
                    tab_index=0,
                    on_click=ChatState.close_chat_image_preview,
                    on_mount=rx.call_script(
                        "const el=document.getElementById('chat-image-preview-overlay'); if(el){el.focus();}"
                    ),
                ),
                rx.fragment(),
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
                                    lambda m, i: rx.cond(
                                        m["role"] == "user",
                                        _chat_user_bubble(m, i),
                                        _chat_assistant_bubble(m, i),
                                    ),
                                ),
                                rx.cond(
                                    (ChatState.streaming_text != "") & (ChatState.regenerating_message_id == ""),
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
                            max_width="100%",
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
                                rx.cond(
                                    ChatState.show_suggestions,
                                    rx.vstack(
                                        rx.text("Try one:", size="1", color=MUTED_TEXT),
                                        rx.flex(
                                            rx.foreach(
                                                ChatState.suggested_prompts,
                                                lambda prompt: rx.button(
                                                    prompt,
                                                    size="1",
                                                    variant="soft",
                                                    color_scheme="green",
                                                    on_click=ChatState.apply_suggestion(prompt),
                                                ),
                                            ),
                                            spacing="2",
                                            wrap="wrap",
                                            justify="center",
                                            width="100%",
                                        ),
                                        spacing="2",
                                        width="100%",
                                        align="center",
                                    ),
                                    rx.fragment(),
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
                    padding_y="0.6rem",
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
            filter=rx.cond(ChatState.history_refreshing, "blur(0.6px)", "none"),
            **_PANEL,
        ),
        rx.cond(
            ChatState.history_refreshing,
            rx.box(
                rx.hstack(
                    rx.icon("loader-circle", size=16, class_name="chat-refresh-spin"),
                    rx.text("Loading chat...", size="1", color=MUTED_TEXT),
                    spacing="2",
                    align="center",
                ),
                position="absolute",
                inset="0",
                display="flex",
                align_items="center",
                justify_content="center",
                bg=_mode("rgba(248,250,252,0.28)", "rgba(3,7,18,0.35)"),
                backdrop_filter="blur(2px)",
                border_radius=RADIUS_LG,
                z_index="2",
            ),
            rx.fragment(),
        ),
        width="100%",
        height="100%",
        min_height="0",
        display="flex",
        flex_direction="column",
        position="relative",
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
                            rx.text(
                                msg,
                                size="1",
                                color=SECONDARY_TEXT,
                                class_name="chat-recent-title",
                                title=msg,
                            ),
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
        rx.cond(
            ChatState.history_refreshing,
            rx.box(
                rx.hstack(
                    rx.icon("loader-circle", size=16, class_name="chat-refresh-spin"),
                    rx.text("Refreshing recents...", size="1", color=MUTED_TEXT),
                    spacing="2",
                    align="center",
                ),
                position="absolute",
                inset="0",
                display="flex",
                align_items="center",
                justify_content="center",
                bg=_mode("rgba(248,250,252,0.3)", "rgba(3,7,18,0.38)"),
                backdrop_filter="blur(2px)",
                border_radius=RADIUS_LG,
                z_index="2",
            ),
            rx.fragment(),
        ),
        padding="0.65rem 0.75rem",
        height="100%",
        backdrop_filter="blur(4px)",
        bg=_PANEL_TINT,
        position="relative",
        filter=rx.cond(ChatState.history_refreshing, "blur(0.6px)", "none"),
        **_PANEL,
    )
