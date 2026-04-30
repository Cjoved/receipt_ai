import reflex as rx

from receipt_ai.core.constants import ICON_SIZE_SM
from receipt_ai.core.theme.tokens import (
    PALETTE_PRIMARY_DEEP,
    RADIUS_FULL,
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
    """Primary nav tab: inactive gray, active green + bottom border (see NAV_SHELL_CSS)."""
    label_row = (
        rx.hstack(
            rx.icon(tag=icon, size=16, color="inherit"),
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
            position="relative",
            isolation="isolate",
            overflow="hidden",
            class_name=rx.cond(active, "nav-tab-btn nav-tab-btn--active", "nav-tab-btn"),
            _focus_visible={
                "outline": "2px solid",
                "outline_color": accent_muted_fg,
                "outline_offset": "2px",
            },
        ),
        href=href,
        class_name="nav-tab-link",
    )


def panel_action_button(label: str, active: bool = False, size: str = "1", on_click=None) -> rx.Component:
    """Filter/sort pill: Files spec (filled green when active)."""
    button_height = "30px" if size == "2" else "auto"
    min_h = "30px" if size == "2" else "28px"
    return rx.button(
        label,
        variant="outline",
        size=size,
        on_click=on_click,
        height=button_height,
        min_height=min_h,
        font_size="12px",
        font_weight=rx.cond(active, "500", "400"),
        line_height="1.2",
        padding="4px 12px",
        border_radius=RADIUS_FULL,
        border="1px solid",
        border_color=rx.cond(active, PALETTE_PRIMARY_DEEP, border_default),
        color=rx.cond(active, theme_pair("#ffffff", "#f9fafb"), theme_pair("#374151", "#d1d5db")),
        bg=rx.cond(active, PALETTE_PRIMARY_DEEP, theme_pair("#ffffff", "#111827")),
        transition="background 0.15s ease, border-color 0.15s ease, color 0.15s ease",
        cursor="pointer",
        _active={"transform": "scale(0.97)", "transition": "transform 0.1s ease"},
        _hover={
            "bg": rx.cond(
                active,
                theme_pair("#145535", "#1a6b45"),
                theme_pair("#f0fdf4", "rgba(96, 202, 114, 0.12)"),
            ),
            "border_color": PALETTE_PRIMARY_DEEP,
            "color": rx.cond(active, theme_pair("#ffffff", "#f9fafb"), PALETTE_PRIMARY_DEEP),
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
    *,
    variant: str = "default",
) -> rx.Component:
    """Toolbar icon button. ``variant="explorer"`` = Files sidebar tool icons."""
    if variant == "explorer":
        return rx.button(
            rx.icon(tag=icon, size=ICON_SIZE_SM, color="inherit"),
            variant="ghost",
            size="1",
            on_click=on_click,
            disabled=disabled,
            title=label,
            position="relative",
            isolation="isolate",
            overflow="hidden",
            min_width="28px",
            min_height="28px",
            border="1px solid transparent",
            border_radius=RADIUS_SM,
            color=rx.cond(disabled, text_muted, theme_pair("#9ca3af", "#6b7280")),
            bg="transparent",
            _hover={
                "color": rx.cond(disabled, text_muted, PALETTE_PRIMARY_DEEP),
                "background": rx.cond(
                    disabled,
                    "transparent",
                    theme_pair("#f0fdf4", "rgba(96, 202, 114, 0.10)"),
                ),
            },
            _focus_visible={
                "outline": "2px solid",
                "outline_color": accent_muted_fg,
                "outline_offset": "1px",
            },
        )
    return rx.button(
        rx.icon(tag=icon, size=ICON_SIZE_SM),
        variant="ghost",
        size="1",
        on_click=on_click,
        disabled=disabled,
        title=label,
        position="relative",
        isolation="isolate",
        overflow="hidden",
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
            "bg": theme_pair("#f3f4f6", "#2d3748"),
            "border_color": border_default,
        },
        _focus_visible={
            "outline": "2px solid",
            "outline_color": accent_muted_fg,
            "outline_offset": "1px",
        },
    )
