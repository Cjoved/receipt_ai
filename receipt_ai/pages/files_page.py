import reflex as rx
from reflex.components.core.breakpoints import breakpoints as bp

from receipt_ai.components.app_footer import app_footer
from receipt_ai.components.file_components import file_tree, files_panel, upload_overlay
from receipt_ai.components.navigation import top_nav
from receipt_ai.components.skip_link import skip_to_main
from receipt_ai.components.ui.buttons import panel_action_button
from receipt_ai.core.constants import (
    APP_BACKGROUND,
    APP_FOREGROUND,
    BORDER_COLOR,
    NAV_HEIGHT,
)
from receipt_ai.core.theme.a11y import A11Y_GLOBAL_CSS
from receipt_ai.core.theme.shell import FILES_SHELL_CSS
from receipt_ai.core.theme.tokens import theme_pair as _mode
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
                    rx.hstack(
                        panel_action_button(
                            "Folders",
                            active=FilesState.files_mobile_view == "tree",
                            on_click=FilesState.show_files_tree_mobile,
                        ),
                        panel_action_button(
                            "Files",
                            active=FilesState.files_mobile_view == "content",
                            on_click=FilesState.show_files_content_mobile,
                        ),
                        width="100%",
                        align="center",
                        class_name="files-mobile-bar",
                    ),
                    rx.box(
                        rx.flex(
                            rx.box(
                                file_tree(),
                                class_name="files-sidebar-col",
                                padding="0.75rem",
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
                                padding="0.75rem 1rem",
                                min_height=shell_min_h,
                            ),
                            class_name="files-split-inner",
                            direction=bp(initial="column", md="row"),
                            width="100%",
                            min_height=shell_min_h,
                            align="stretch",
                        ),
                        class_name="files-shell",
                        id="files-split-root",
                        width="100%",
                        data_files_view=FilesState.files_mobile_view,
                        style={
                            "--files-sidebar-pct": FilesState.sidebar_width_css,
                            "--files-border": BORDER_COLOR,
                            "--files-canvas": _mode("#f9fafb", "#030712"),
                            "--files-subtle": _mode("#f3f4f6", "#1f2937"),
                            "--files-divider-hover": _mode("rgba(22, 163, 74, 0.14)", "rgba(34, 197, 94, 0.22)"),
                        },
                    ),
                    app_footer(),
                    spacing="0",
                    width="100%",
                    style={
                        "--files-border": BORDER_COLOR,
                        "--files-canvas": _mode("#f9fafb", "#030712"),
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
                position="relative",
                width="100%",
            ),
            id="main-content",
            tab_index=-1,
            width="100%",
            flex="1",
            outline="none",
        ),
        upload_overlay(),
        bg=APP_BACKGROUND,
        color=APP_FOREGROUND,
        min_height="100vh",
        display="flex",
        flex_direction="column",
    )
