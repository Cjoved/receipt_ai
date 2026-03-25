import reflex as rx

from receipt_ai.components.file_components import file_tree, files_panel
from receipt_ai.components.navigation import top_nav
from receipt_ai.core.constants import APP_BACKGROUND, APP_FOREGROUND, BORDER_COLOR


def files_page() -> rx.Component:
    return rx.box(
        top_nav("files"),
        rx.hstack(
            rx.box(
                file_tree(),
                width="24%",
                min_width="260px",
                padding="1rem",
                border_right=f"1px solid {BORDER_COLOR}",
            ),
            rx.box(files_panel(), width="76%", padding="1rem"),
            width="100%",
            align="start",
            min_height="calc(100vh - 74px)",
        ),
        bg=APP_BACKGROUND,
        color=APP_FOREGROUND,
        min_height="100vh",
    )
