import reflex as rx
from reflex.components.core.breakpoints import breakpoints as bp

from receipt_ai.components.chat_components import (
    chat_center_panel,
    chat_history,
    recent_chats_panel,
)
from receipt_ai.components.navigation import top_nav
from receipt_ai.components.skip_link import skip_to_main
from receipt_ai.core.constants import APP_FOREGROUND, BORDER_COLOR, NAV_HEIGHT
from receipt_ai.core.theme.a11y import A11Y_GLOBAL_CSS
from receipt_ai.core.theme.shell import CHAT_MARKDOWN_CSS, CHAT_SHELL_CSS
from receipt_ai.core.theme.tokens import chat_main_bg, chat_page_bg, chat_sidebar_bg, theme_pair as _mode
from receipt_ai.features.chat.state import ChatState


def chat_page() -> rx.Component:
    """Chat page — true viewport-locked layout, internal scroll only."""
    return rx.box(
        skip_to_main(),
        top_nav("chat"),
        rx.el.style(A11Y_GLOBAL_CSS + CHAT_SHELL_CSS + CHAT_MARKDOWN_CSS),
        rx.el.main(
            rx.vstack(
                # ── Mobile toolbar (history drawer trigger) ───────────────
                rx.hstack(
                    rx.button(
                        rx.hstack(
                            rx.icon("panel_left", size=15),
                            rx.text("History", size="2", weight="medium"),
                            spacing="2",
                            align="center",
                        ),
                        on_click=ChatState.open_chat_history_drawer,
                        variant="soft",
                        color_scheme="green",
                        border_radius="8px",
                        min_height="34px",
                        aria_label="Open chat history",
                    ),
                    rx.spacer(),
                    width="100%",
                    align="center",
                    flex_shrink="0",
                    class_name="chat-mobile-toolbar",
                ),
                # ── Three-column shell ─────────────────────────────────────
                rx.box(
                    rx.flex(
                        # Left: history sidebar
                        rx.box(
                            chat_history(),
                            class_name="chat-sidebar-col",
                            padding="0",
                            border_right=f"1px solid {BORDER_COLOR}",
                            bg=chat_sidebar_bg,
                            # sidebar scrolls internally — chat_history() owns its overflow
                        ),
                        # Divider grip
                        rx.box(
                            rx.box(
                                class_name="chat-divider-grip",
                                on_mouse_down=ChatState.on_chat_divider_mouse_down,
                                title="Drag to resize history",
                                aria_label="Resize history panel",
                            ),
                            class_name="chat-divider-col",
                            padding_y="0.5rem",
                            align_items="center",
                            justify_content="center",
                        ),
                        # Right: center thread + recent column
                        rx.box(
                            rx.flex(
                                rx.box(
                                    chat_center_panel(),
                                    class_name="chat-center-wrap",
                                ),
                                rx.box(
                                    recent_chats_panel(),
                                    class_name="chat-recent-col",
                                    bg=chat_sidebar_bg,
                                    border_left=f"1px solid {BORDER_COLOR}",
                                ),
                                class_name="chat-inner-split",
                                direction=bp(initial="column", lg="row"),
                                width="100%",
                                align="stretch",
                                spacing="0",
                            ),
                            class_name="chat-main-col",
                            padding="0",
                            bg=chat_main_bg,
                        ),
                        class_name="chat-split-inner",
                        direction=bp(initial="column", md="row"),
                        width="100%",
                        align="stretch",
                    ),
                    class_name="chat-shell",
                    id="chat-split-root",
                    width="100%",
                    # Grows to fill whatever height the vstack gives it
                    flex="1 1 0%",
                    min_height="0",
                    overflow="hidden",
                    data_chat_view=ChatState.chat_mobile_view,
                    style={
                        "--chat-sidebar-pct": ChatState.chat_sidebar_width_css,
                        "--chat-sidebar-px": ChatState.chat_sidebar_width_css,
                        "--chat-border": BORDER_COLOR,
                        "--chat-canvas": chat_page_bg,
                        "--chat-main-bg": chat_main_bg,
                        "--chat-sidebar-bg": chat_sidebar_bg,
                        "--chat-subtle": _mode("#f3f4f6", "#1f2937"),
                        "--chat-divider-hover": _mode("rgba(22, 163, 74, 0.14)", "rgba(34, 197, 94, 0.22)"),
                    },
                ),
                rx.cond(
                    ChatState.chat_history_drawer_open,
                    rx.box(
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.text("History", size="3", weight="bold"),
                                    rx.spacer(),
                                    rx.button(
                                        rx.icon("x", size=16),
                                        variant="ghost",
                                        size="2",
                                        on_click=ChatState.close_chat_history_drawer,
                                        aria_label="Close history drawer",
                                        min_width="34px",
                                        min_height="34px",
                                    ),
                                    width="100%",
                                    align="center",
                                ),
                                rx.box(
                                    chat_history(),
                                    class_name="chat-mobile-drawer-history",
                                ),
                                spacing="3",
                                width="100%",
                                height="100%",
                                align="stretch",
                            ),
                            class_name="chat-mobile-drawer-panel",
                            on_click=rx.call_script("event.stopPropagation()"),
                        ),
                        class_name="chat-mobile-drawer-backdrop",
                        on_click=ChatState.close_chat_history_drawer,
                    ),
                    rx.fragment(),
                ),
                spacing="0",
                width="100%",
                # Fill the full height of <main> without shrinking
                height="100%",
                min_height="0",
                overflow="hidden",
                align="stretch",
                style={
                    "--chat-border": BORDER_COLOR,
                    "--chat-canvas": chat_page_bg,
                    "--chat-main-bg": chat_main_bg,
                    "--chat-sidebar-bg": chat_sidebar_bg,
                    "--chat-subtle": _mode("#f3f4f6", "#1f2937"),
                },
            ),
            id="main-content",
            tab_index=-1,
            width="100%",
            # ── KEY FIX: main fills the remaining viewport height ──────────
            # height = 100vh minus the nav bar; flex=1 lets the parent share
            # the space, overflow=hidden prevents page-level scroll.
            height=f"calc(100vh - {NAV_HEIGHT})",
            overflow="hidden",
            flex="1 1 0%",
            min_height="0",
            outline="none",
            display="flex",
            flex_direction="column",
        ),
        bg=chat_page_bg,
        color=APP_FOREGROUND,
        # ── Root container: fixed to the viewport ─────────────────────────
        height="100vh",
        overflow="hidden",
        display="flex",
        flex_direction="column",
    )