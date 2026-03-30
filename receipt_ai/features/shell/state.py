"""Shell UI state: top nav mobile sheet + optional viewport (Phase 5)."""

import reflex as rx


class NavState(rx.State):
    """Primary navigation: mobile sheet toggle (Technical AI hamburger pattern)."""

    mobile_open: bool = False
    # Updated from rx.window_event_listener on_resize (for future responsive logic / debugging).
    viewport_width: int = 0
    viewport_height: int = 0

    def toggle_mobile_nav(self) -> None:
        self.mobile_open = not self.mobile_open

    def close_mobile_nav(self) -> None:
        self.mobile_open = False

    def on_viewport_resize(self, width: int, height: int) -> None:
        """Keep window dimensions in state (orientation / split-view friendly)."""
        self.viewport_width = int(width)
        self.viewport_height = int(height)
