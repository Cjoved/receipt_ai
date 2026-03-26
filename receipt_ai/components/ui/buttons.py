import reflex as rx
from receipt_ai.core.constants import ICON_SIZE_SM


def nav_button(label: str, href: str, active: bool) -> rx.Component:
    """Navigation button with active/inactive styles."""
    # Wrap a button in a link for client-side navigation.
    return rx.link(
        rx.button(label, variant="soft" if active else "outline"),
        href=href,
    )


def panel_action_button(label: str, active: bool = False, size: str = "1", on_click=None) -> rx.Component:
    """Reusable action button for panel controls."""
    # Shared pattern for simple panel actions.
    return rx.button(
        label,
        variant=rx.cond(active, "soft", "outline"),
        size=size,
        on_click=on_click,
    )


def primary_action_button(label: str, width: str = "auto") -> rx.Component:
    """Reusable primary action button."""
    # Main CTA style used in side panels.
    return rx.button(label, width=width, color_scheme="green")

def icon_button(
    icon: str,
    label: str,
    on_click=None,
    disabled: bool = False,
    active: bool = False,
) -> rx.Component:
    """Small icon-only button used in toolbars."""
    return rx.button(
        # Icon uses global sizing token for consistency.
        rx.icon(tag=icon, size=ICON_SIZE_SM),
        variant="ghost",
        size="2",
        on_click=on_click,
        disabled=disabled,
        title=label,
        border_radius="8px",
        bg=rx.cond(active, rx.color("blue", 4), "transparent"),
        _hover={"bg": rx.color("blue", 4)},
        _focus_visible={
            "outline": f"2px solid {rx.color('blue', 8)}",
            "outline_offset": "1px",
        },
    )