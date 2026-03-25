import reflex as rx


class AppState(rx.State):
    """Global app state for cross-feature UI state."""

    app_title: str = "LeadsTech"
