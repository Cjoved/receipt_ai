import reflex as rx

from receipt_ai.components.file_components import file_tree, files_panel, upload_overlay
from receipt_ai.components.navigation import top_nav
from receipt_ai.components.skip_link import skip_to_main
from receipt_ai.core.constants import APP_FOREGROUND, BORDER_COLOR, NAV_HEIGHT
from receipt_ai.core.theme.a11y import A11Y_GLOBAL_CSS
from receipt_ai.core.theme.shell import FILES_SHELL_CSS
from receipt_ai.core.theme.tokens import chat_main_bg, chat_page_bg, theme_pair as _mode
from receipt_ai.features.files.state import FilesState


def files_page() -> rx.Component:
    """Files page with resizable explorer, content panel, and mobile tree/content switch."""
    shell_min_h = f"calc(100vh - {NAV_HEIGHT})"
    return rx.box(
        skip_to_main(),
        top_nav("files"),
        rx.el.style(A11Y_GLOBAL_CSS + FILES_SHELL_CSS),
        rx.el.main(
            rx.box(
                rx.vstack(
                    rx.box(
                        rx.cond(
                            FilesState.sidebar_open,
                            rx.box(
                                position="fixed",
                                top="0",
                                left="0",
                                width="100vw",
                                height="100vh",
                                background="rgba(0,0,0,0.4)",
                                z_index="40",
                                on_click=FilesState.close_sidebar,
                                display=["flex", "none", "none", "none"],
                            ),
                        ),
                        rx.flex(
                            rx.box(
                                file_tree(),
                                class_name="files-sidebar-col",
                                padding="12px",
                                border_right=f"1px solid {BORDER_COLOR}",
                            ),
                            rx.box(
                                rx.box(class_name="files-divider-grip"),
                                class_name="files-divider-col",
                                padding_y="0.5rem",
                                align_items="center",
                                justify_content="center",
                                on_mouse_down=FilesState.on_explorer_divider_mouse_down,
                                title="Drag to resize explorer",
                                aria_label="Resize explorer panel",
                            ),
                            rx.box(
                                files_panel(),
                                class_name="files-main-col",
                                padding=["12px", "16px", "20px", "24px"],
                                flex="1",
                                display="flex",
                                flex_direction="column",
                                overflow_x="hidden",
                                overflow_y="auto",
                                width=["100%", "auto", "auto", "auto"],
                                min_height="0",
                            ),
                            class_name="files-split-inner",
                            display="flex",
                            flex_direction=rx.breakpoints(initial="column", md="row"),
                            width="100%",
                            height="100%",
                            min_height="0",
                            align="stretch",
                            overflow="hidden",
                            position="relative",
                        ),
                        class_name="files-shell",
                        id="files-split-root",
                        width="100%",
                        height="100%",
                        min_height="0",
                        data_files_view=rx.cond(FilesState.sidebar_open, "tree", "content"),
                        style={
                            "--files-sidebar-pct": FilesState.sidebar_width_css,
                            "--files-border": BORDER_COLOR,
                            "--files-canvas": chat_page_bg,
                            "--files-main-bg": chat_main_bg,
                            "--files-subtle": _mode("#f3f4f6", "#1f2937"),
                            "--files-divider-hover": _mode("rgba(22, 163, 74, 0.14)", "rgba(34, 197, 94, 0.22)"),
                        },
                        position="relative",
                        overflow="hidden",
                    ),
                    spacing="0",
                    width="100%",
                    height="100%",
                    min_height="0",
                    style={
                        "--files-border": BORDER_COLOR,
                        "--files-canvas": chat_page_bg,
                        "--files-main-bg": chat_main_bg,
                        "--files-subtle": _mode("#f3f4f6", "#1f2937"),
                    },
                ),
                rx.cond(
                    FilesState.is_loading_files,
                    rx.box(
                        rx.vstack(
                            rx.spinner(size="3"),
                            rx.heading("Loading files from Wasabi...", size="4", color="white"),
                            rx.text(
                                "Please wait while we fetch your folder list.",
                                size="2",
                                color=rx.color("gray", 4),
                            ),
                            spacing="3",
                            align="center",
                        ),
                        position="absolute",
                        inset="0",
                        z_index="40",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        background="rgba(2, 6, 23, 0.34)",
                        backdrop_filter="blur(3px)",
                        padding="1rem",
                    ),
                ),
                rx.button(
                    rx.icon("menu", size=20, color="white"),
                    on_click=FilesState.toggle_sidebar,
                    display=["flex", "none", "none", "none"],
                    position="fixed",
                    bottom="16px",
                    right="16px",
                    z_index="100",
                    background="#1a6b45",
                    color="white",
                    border_radius="50%",
                    width="48px",
                    height="48px",
                    min_width="48px",
                    min_height="48px",
                    box_shadow="0 4px 12px rgba(26,107,69,0.3)",
                    _hover={"background": "#145535"},
                ),
                position="relative",
                width="100%",
                height="100%",
            ),
            id="main-content",
            tab_index=-1,
            width="100%",
            flex="1 1 0%",
            height=shell_min_h,
            min_height="0",
            overflow="hidden",
            outline="none",
            display="flex",
            flex_direction="column",
        ),
        upload_overlay(),
        bg=chat_page_bg,
        color=APP_FOREGROUND,
        height="100vh",
        overflow="hidden",
        display="flex",
        flex_direction="column",
    )