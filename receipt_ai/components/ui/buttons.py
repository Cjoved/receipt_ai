import reflex as rx


def nav_button(label: str, href: str, active: bool) -> rx.Component:
    """Navigation button with active/inactive styles."""
    # Wrap a button in a link for client-side navigation.
    return rx.link(
        rx.button(label, variant="soft" if active else "outline"),
        href=href,
    )


def panel_action_button(label: str, active: bool = False, size: str = "1") -> rx.Component:
    """Reusable action button for panel controls."""
    return rx.button(label, variant="soft" if active else "outline", size=size)


def primary_action_button(label: str, width: str = "auto") -> rx.Component:
    """Reusable primary action button."""
    return rx.button(label, width=width, color_scheme="green")

def icon_button(icon: str, label: str, on_click=None) -> rx.Component:
    """Small icon-only button used in toolbars."""
    return rx.button(
        rx.icon(tag=icon, size=16),
        variant="ghost",
        size="1",
        on_click=on_click,
        title=label,
    )