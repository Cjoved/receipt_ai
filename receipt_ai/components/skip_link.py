"""Skip navigation link (WCAG 2.4.1)."""

import reflex as rx


def skip_to_main() -> rx.Component:
    """First tab stop: jump to ``#main-content``."""
    return rx.link(
        "Skip to main content",
        href="#main-content",
        class_name="skip-to-main",
    )
