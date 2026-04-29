import reflex as rx

from receipt_ai.core.constants import ICON_SIZE_SM, SECONDARY_TEXT
from receipt_ai.core.theme.tokens import (
    RADIUS_MD,
    RADIUS_SM,
    accent_solid,
    accent_solid_hover,
    accent_muted_fg,
    accent_soft_bg,
    accent_soft_bg_strong,
    border_default,
    text_muted,
    text_secondary,
    theme_pair,
)


def nav_button(label: str, href: str, active: bool, *, icon: str | None = None) -> rx.Component:
    """Navigation link styled like Technical AI (agri soft pill when active)."""
    label_row = (
        rx.hstack(
            rx.icon(tag=icon, size=16),
            label,
            spacing="2",
            align="center",
        )
        if icon
        else label
    )
    return rx.link(
        rx.button(
            label_row,
            variant="ghost",
            size="2",
            border_radius=RADIUS_MD,
            weight="600" if active else "500",
            bg=accent_soft_bg if active else "transparent",
            color=accent_muted_fg if active else SECONDARY_TEXT,
            _hover={
                "bg": accent_soft_bg_strong if active else theme_pair("#f3f4f6", "#1f2937"),
            },
        ),
        href=href,
    )


def panel_action_button(label: str, active: bool = False, size: str = "1", on_click=None) -> rx.Component:
    """Reusable chip for filters/sort (agri accent when active)."""
    button_height = "30px" if size == "2" else "24px"
    return rx.button(
        label,
        variant="outline",
        size=size,
        on_click=on_click,
        height=button_height,
        border_radius=RADIUS_SM,
        border_color=rx.cond(active, accent_muted_fg, border_default),
        color=rx.cond(active, accent_muted_fg, text_secondary),
        bg=rx.cond(active, accent_soft_bg, "transparent"),
        _hover={
            "bg": theme_pair("#ecfdf5", "rgba(34, 197, 94, 0.12)"),
            "border_color": accent_muted_fg,
        },
    )


def primary_action_button(label: str, width: str = "auto") -> rx.Component:
    """Primary CTA (agri)."""
    return rx.button(
        label,
        width=width,
        bg=accent_solid,
        color=theme_pair("#ffffff", "#102214"),
        _hover={"bg": accent_solid_hover},
        _active={"transform": "translateY(1px)"},
    )


def icon_button(
    icon: str,
    label: str,
    on_click=None,
    disabled: bool = False,
    active: bool = False,
) -> rx.Component:
    """Toolbar icon button; active uses agri soft surface."""
    return rx.button(
        rx.icon(tag=icon, size=ICON_SIZE_SM),
        variant="ghost",
        size="1",
        on_click=on_click,
        disabled=disabled,
        title=label,
        min_width="28px",
        min_height="28px",
        border="1px solid transparent",
        border_radius=RADIUS_SM,
        color=rx.cond(
            disabled,
            text_muted,
            rx.cond(active, accent_muted_fg, text_secondary),
        ),
        bg=rx.cond(active, accent_soft_bg_strong, "transparent"),
        border_color=rx.cond(active, accent_muted_fg, "transparent"),
        _hover={
            "bg": theme_pair("#f3f4f6", "#1f2937"),
            "border_color": border_default,
        },
        _focus_visible={
            "outline": "2px solid",
            "outline_color": accent_muted_fg,
            "outline_offset": "1px",
        },
    )
