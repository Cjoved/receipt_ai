import reflex as rx
from reflex.components.core.breakpoints import breakpoints as bp

from receipt_ai.components.app_footer import app_footer
from receipt_ai.components.chat_components import (
    chat_center_panel,
    chat_history,
    recent_chats_panel,
)
from receipt_ai.components.navigation import top_nav
from receipt_ai.components.skip_link import skip_to_main
from receipt_ai.components.ui.buttons import panel_action_button
from receipt_ai.core.constants import APP_BACKGROUND, APP_FOREGROUND, BORDER_COLOR, NAV_HEIGHT
from receipt_ai.core.theme.a11y import A11Y_GLOBAL_CSS
from receipt_ai.core.theme.shell import CHAT_MARKDOWN_CSS, CHAT_SHELL_CSS
from receipt_ai.core.theme.tokens import theme_pair as _mode
from receipt_ai.features.chat.state import ChatState


def chat_page() -> rx.Component:
    """Chat page with resizable history rail, center thread, recent column, and mobile switch."""
    shell_min_h = f"calc(100vh - {NAV_HEIGHT})"
    return rx.box(
        skip_to_main(),
        top_nav("chat"),
        rx.el.style(A11Y_GLOBAL_CSS + CHAT_SHELL_CSS + CHAT_MARKDOWN_CSS),
        rx.el.main(
            rx.vstack(
                rx.hstack(
                    panel_action_button(
                        "History",
                        active=ChatState.chat_mobile_view == "history",
                        on_click=ChatState.show_chat_history_mobile,
                    ),
                    panel_action_button(
                        "Chat",
                        active=ChatState.chat_mobile_view == "content",
                        on_click=ChatState.show_chat_content_mobile,
                    ),
                    width="100%",
                    align="center",
                    class_name="chat-mobile-bar",
                ),
                rx.box(
                    rx.flex(
                        rx.box(
                            chat_history(),
                            class_name="chat-sidebar-col",
                            padding="0.75rem",
                            border_right=f"1px solid {BORDER_COLOR}",
                        ),
                        rx.box(
                            rx.box(class_name="chat-divider-grip"),
                            class_name="chat-divider-col",
                            padding_y="0.5rem",
                            align_items="center",
                            justify_content="center",
                            on_mouse_down=ChatState.on_chat_divider_mouse_down,
                            title="Drag to resize history",
                            aria_label="Resize history panel",
                        ),
                        rx.box(
                            rx.flex(
                                rx.box(
                                    chat_center_panel(),
                                    class_name="chat-center-wrap",
                                    min_height=shell_min_h,
                                ),
                                rx.box(
                                    recent_chats_panel(),
                                    class_name="chat-recent-col",
                                ),
                                class_name="chat-inner-split",
                                direction=bp(initial="column", lg="row"),
                                width="100%",
                                min_height=shell_min_h,
                                align="stretch",
                                spacing="4",
                            ),
                            class_name="chat-main-col",
                            padding="0.75rem 1rem",
                            min_height=shell_min_h,
                        ),
                        class_name="chat-split-inner",
                        direction=bp(initial="column", md="row"),
                        width="100%",
                        min_height=shell_min_h,
                        align="stretch",
                    ),
                    class_name="chat-shell",
                    id="chat-split-root",
                    width="100%",
                    data_chat_view=ChatState.chat_mobile_view,
                    style={
                        "--chat-sidebar-pct": ChatState.chat_sidebar_width_css,
                        "--chat-border": BORDER_COLOR,
                        "--chat-canvas": _mode("#f9fafb", "#030712"),
                        "--chat-subtle": _mode("#f3f4f6", "#1f2937"),
                        "--chat-divider-hover": _mode("rgba(22, 163, 74, 0.14)", "rgba(34, 197, 94, 0.22)"),
                    },
                ),
                app_footer(),
                spacing="0",
                width="100%",
                style={
                    "--chat-border": BORDER_COLOR,
                    "--chat-canvas": _mode("#f9fafb", "#030712"),
                    "--chat-subtle": _mode("#f3f4f6", "#1f2937"),
                },
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
