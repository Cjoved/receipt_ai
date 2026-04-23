import reflex as rx

from receipt_ai.components.ui.buttons import nav_button
from receipt_ai.core.constants import APP_FOREGROUND, MUTED_TEXT, SECONDARY_TEXT
from receipt_ai.core.theme.shell import NAV_SHELL_CSS
from receipt_ai.core.theme.tokens import (
    BLUR_NAV,
    NAV_HEIGHT,
    RADIUS_FULL,
    RADIUS_MD,
    SHADOW_NAV,
    accent_muted_fg,
    accent_soft_bg,
    border_default,
    nav_border,
    nav_surface,
    surface_panel,
    text_muted,
    text_primary,
    theme_pair,
)
from receipt_ai.features.auth.state import AuthState
from receipt_ai.features.shell.state import NavState


def _notif_popover() -> rx.Component:
    """Bell + panel (empty state); WebSocket wiring comes later."""
    return rx.popover.root(
        rx.popover.trigger(
            rx.button(
                rx.icon("bell", size=18, color=SECONDARY_TEXT),
                variant="ghost",
                size="2",
                title="Notifications",
            ),
        ),
        rx.popover.content(
            rx.vstack(
                rx.hstack(
                    rx.heading("Notifications", size="3", color=APP_FOREGROUND),
                    width="100%",
                    align="center",
                    padding_bottom="0.5rem",
                    border_bottom=f"1px solid {border_default}",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("bell", size=32, color=MUTED_TEXT),
                        rx.text("No notifications yet", size="2", color=MUTED_TEXT),
                        spacing="2",
                        align="center",
                    ),
                    padding_y="2rem",
                    width="100%",
                ),
                spacing="0",
                width="100%",
            ),
            size="2",
            width="320px",
            side="bottom",
            align="end",
            side_offset=8,
        ),
        modal=False,
    )


def _account_menu() -> rx.Component:
    """Avatar + dropdown (TA account menu); auth routes when backend exists."""
    return rx.dropdown_menu.root(
        rx.dropdown_menu.trigger(
            rx.button(
                rx.hstack(
                    rx.box(
                        "R",
                        width="28px",
                        height="28px",
                        border_radius=RADIUS_FULL,
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        font_size="12px",
                        font_weight="700",
                        bg=accent_soft_bg,
                        color=accent_muted_fg,
                    ),
                    rx.text(
                        AuthState.user_display_name,
                        size="2",
                        weight="medium",
                        color=APP_FOREGROUND,
                        class_name="nav-account-label",
                    ),
                    rx.icon("chevron-down", size=14, color=SECONDARY_TEXT),
                    spacing="2",
                    align="center",
                ),
                variant="ghost",
                size="2",
            ),
        ),
        rx.dropdown_menu.content(
            rx.box(
                rx.text(AuthState.user_display_name, weight="bold", size="2", color=text_primary),
                rx.text(AuthState.email, size="1", color=text_muted),
                padding="12px",
                border_bottom=f"1px solid {border_default}",
            ),
            rx.dropdown_menu.separator(),
            rx.dropdown_menu.item("Profile"),
            rx.dropdown_menu.item("Log out", on_click=AuthState.logout),
            side="bottom",
            align="end",
            size="2",
        ),
        modal=False,
    )


def _mobile_nav_toggle() -> rx.Component:
    return rx.button(
        rx.cond(
            NavState.mobile_open,
            rx.icon("x", size=20, color=SECONDARY_TEXT),
            rx.icon("menu", size=20, color=SECONDARY_TEXT),
        ),
        variant="ghost",
        size="2",
        on_click=NavState.toggle_mobile_nav,
        title="Menu",
        class_name="nav-mobile-only",
    )


def _mobile_nav_link(
    *,
    label: str,
    href: str,
    icon: str,
    active: bool,
) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.icon(tag=icon, size=16, color=accent_muted_fg if active else SECONDARY_TEXT),
            label,
            spacing="2",
            align="center",
        ),
        href=href,
        on_click=NavState.close_mobile_nav,
        class_name="nav-mobile-link",
        color=APP_FOREGROUND,
        bg=accent_soft_bg if active else "transparent",
        width="100%",
        border_radius=RADIUS_MD,
        _hover={
            "background": theme_pair("#f3f4f6", "#1f2937"),
        },
    )


def top_nav(active_page: str) -> rx.Component:
    """Sticky frosted top bar (Technical AI shell): logo, routes, theme, account."""
    files_active = active_page == "files"
    chat_active = active_page == "chat"
    return rx.fragment(
        rx.window_event_listener(on_resize=NavState.on_viewport_resize),
        rx.el.style(NAV_SHELL_CSS),
        rx.el.header(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.link(
                            rx.hstack(
                                rx.icon("leaf", size=18, color="green"),
                                rx.heading("Receipt AI", size="4", color=APP_FOREGROUND),
                                spacing="2",
                                align="center",
                            ),
                            href=AuthState.home_route,
                            class_name="nav-brand-link",
                        ),
                        rx.hstack(
                            rx.cond(
                                AuthState.can_access_files,
                                nav_button("Files", "/files", files_active, icon="folder"),
                            ),
                            nav_button("Chat", "/chat", chat_active, icon="message-circle"),
                            spacing="2",
                            class_name="nav-desktop-only",
                        ),
                        spacing="3",
                        align="center",
                    ),
                    rx.hstack(
                        _notif_popover(),
                        rx.color_mode.button(),
                        _account_menu(),
                        _mobile_nav_toggle(),
                        spacing="2",
                        align="center",
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                    class_name="nav-shell-inner nav-shell-row",
                ),
                rx.box(
                    rx.vstack(
                        rx.cond(
                            AuthState.can_access_files,
                            _mobile_nav_link(
                                label="Files",
                                href="/files",
                                icon="folder",
                                active=files_active,
                            ),
                        ),
                        _mobile_nav_link(
                            label="Chat",
                            href="/chat",
                            icon="message-circle",
                            active=chat_active,
                        ),
                        spacing="1",
                        width="100%",
                        align_items="stretch",
                    ),
                    class_name="nav-mobile-panel",
                    display=rx.cond(NavState.mobile_open, "flex", "none"),
                    flex_direction="column",
                    width="100%",
                    border_top=f"1px solid {nav_border}",
                    bg=surface_panel,
                    padding_top="0.5rem",
                    padding_bottom="0.75rem",
                    padding_x="1rem",
                ),
                spacing="0",
                width="100%",
            ),
            position="sticky",
            top="0",
            z_index="50",
            width="100%",
            border_bottom=f"1px solid {nav_border}",
            bg=nav_surface,
            backdrop_filter=f"blur({BLUR_NAV})",
            box_shadow=SHADOW_NAV,
            min_height=NAV_HEIGHT,
            aria_label="Primary navigation",
        ),
    )
