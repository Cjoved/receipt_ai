"""Site footer landmark (Phase 10)."""

import reflex as rx

from receipt_ai.core.constants import BORDER_COLOR, MUTED_TEXT


def app_footer() -> rx.Component:
    """Compact footer with contentinfo role."""
    return rx.el.footer(
        rx.text(
            "Receipt AI — Agricultural receipts and document workspace.",
            size="1",
            color=MUTED_TEXT,
            text_align="center",
        ),
        width="100%",
        style={
            "paddingTop": "0.85rem",
            "paddingBottom": "max(0.85rem, env(safe-area-inset-bottom, 0px))",
            "paddingLeft": "max(1rem, env(safe-area-inset-left, 0px))",
            "paddingRight": "max(1rem, env(safe-area-inset-right, 0px))",
        },
        border_top=f"1px solid {BORDER_COLOR}",
    )
