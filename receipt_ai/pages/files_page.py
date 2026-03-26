import reflex as rx

from receipt_ai.components.file_components import file_tree, files_panel, upload_overlay
from receipt_ai.components.navigation import top_nav
from receipt_ai.core.constants import APP_BACKGROUND, APP_FOREGROUND, BORDER_COLOR


def files_page() -> rx.Component:
    """Files page with sidebar explorer, content panel, and global upload overlay."""
    return rx.box(
        # Top app navigation.
        top_nav("files"),
        # Main two-column content area.
        rx.hstack(
            # Left sidebar column.
            rx.box(
                file_tree(),
                width="24%",
                min_width="260px",
                padding="1rem",
                border_right=f"1px solid {BORDER_COLOR}",
            ),
            # Right content column.
            rx.box(files_panel(), width="76%", padding="1rem"),
            width="100%",
            align="start",
            min_height="calc(100vh - 74px)",
        ),
        # Global upload modal (toolbar upload icon). Reflex `rx.box` has no on_drag_* triggers;
        # whole-window drag-to-open would need a custom component or script later.
        upload_overlay(),
        bg=APP_BACKGROUND,
        color=APP_FOREGROUND,
        min_height="100vh",
    )
