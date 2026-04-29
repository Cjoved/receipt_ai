import reflex as rx

from receipt_ai.components.app_footer import app_footer
from receipt_ai.components.navigation import top_nav
from receipt_ai.components.skip_link import skip_to_main
from receipt_ai.core.constants import APP_BACKGROUND, APP_FOREGROUND
from receipt_ai.core.theme.a11y import A11Y_GLOBAL_CSS
from receipt_ai.core.theme.tokens import accent_solid, accent_soft_bg, success_fg
from receipt_ai.features.auth.state import AuthState


def _readonly_row(label: str, value) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=rx.color("gray", 10)),
        rx.text(value, size="3", color=APP_FOREGROUND, weight="medium"),
        spacing="1",
        align="start",
        width="100%",
    )


def settings_page() -> rx.Component:
    return rx.box(
        skip_to_main(),
        top_nav("settings"),
        rx.el.style(A11Y_GLOBAL_CSS),
        rx.el.main(
            rx.center(
                rx.container(
                rx.vstack(
                    rx.vstack(
                        rx.heading("Profile", size=rx.breakpoints(initial="6", md="7")),
                        rx.text(
                            "Manage your account identity and workspace preferences.",
                            size=rx.breakpoints(initial="2", md="3"),
                            color=rx.color("gray", 10),
                        ),
                        spacing="2",
                        align="start",
                        width="100%",
                    ),
                    rx.form(
                        rx.vstack(
                            rx.card(
                                rx.vstack(
                                    rx.hstack(
                                        rx.hstack(
                                            rx.center(
                                                rx.icon("user", size=18, color="white"),
                                                width="34px",
                                                height="34px",
                                                border_radius="10px",
                                                bg=accent_solid,
                                            ),
                                            rx.vstack(
                                                rx.heading("Profile Overview", size="4"),
                                                rx.text("Your account status and role.", size="2", color=rx.color("gray", 10)),
                                                spacing="0",
                                                align="start",
                                            ),
                                            spacing="3",
                                            align="center",
                                        ),
                                        rx.hstack(
                                            rx.badge(AuthState.primary_role, color_scheme="green", variant="soft"),
                                            rx.badge(
                                                rx.cond(AuthState.is_authenticated, "Active", "Inactive"),
                                                color_scheme=rx.cond(AuthState.is_authenticated, "grass", "tomato"),
                                                variant="soft",
                                            ),
                                            spacing="2",
                                        ),
                                        justify="between",
                                        align=rx.breakpoints(initial="start", md="center"),
                                        width="100%",
                                        flex_wrap="wrap",
                                        spacing="2",
                                    ),
                                    _readonly_row("Email", AuthState.email),
                                    spacing="4",
                                    width="100%",
                                    align="start",
                                ),
                                width="100%",
                                size="3",
                            ),
                            rx.grid(
                                rx.card(
                                    rx.vstack(
                                        rx.text("Display name", size="2", weight="medium"),
                                        rx.input(
                                            value=AuthState.settings_display_name,
                                            on_change=AuthState.set_settings_display_name,
                                            on_focus=AuthState.clear_settings_feedback,
                                            width="100%",
                                        ),
                                        spacing="1",
                                        width="100%",
                                        align="start",
                                    ),
                                    rx.text(
                                        "Used across chat, files, and audit-friendly activity labels.",
                                        size="1",
                                        color=rx.color("gray", 10),
                                    ),
                                    spacing="4",
                                    width="100%",
                                    align="start",
                                ),
                                rx.card(
                                    rx.vstack(
                                        rx.heading("Preferences", size="4"),
                                        rx.vstack(
                                            rx.text("Default page after sign in", size="2", weight="medium"),
                                            rx.hstack(
                                                rx.button(
                                                    "Chat",
                                                    type="button",
                                                    variant=rx.cond(
                                                        AuthState.settings_default_page == "chat", "solid", "soft"
                                                    ),
                                                    bg=rx.cond(
                                                        AuthState.settings_default_page == "chat",
                                                        accent_solid,
                                                        accent_soft_bg,
                                                    ),
                                                    color=rx.cond(
                                                        AuthState.settings_default_page == "chat",
                                                        "white",
                                                        APP_FOREGROUND,
                                                    ),
                                                    on_click=AuthState.set_settings_default_page("chat"),
                                                ),
                                                rx.cond(
                                                    AuthState.can_access_files,
                                                    rx.button(
                                                        "Files",
                                                        type="button",
                                                        variant=rx.cond(
                                                            AuthState.settings_default_page == "files", "solid", "soft"
                                                        ),
                                                        bg=rx.cond(
                                                            AuthState.settings_default_page == "files",
                                                            accent_solid,
                                                            accent_soft_bg,
                                                        ),
                                                        color=rx.cond(
                                                            AuthState.settings_default_page == "files",
                                                            "white",
                                                            APP_FOREGROUND,
                                                        ),
                                                        on_click=AuthState.set_settings_default_page("files"),
                                                    ),
                                                ),
                                                spacing="2",
                                                flex_wrap="wrap",
                                                width="100%",
                                            ),
                                            spacing="1",
                                            width="100%",
                                            align="start",
                                        ),
                                        rx.hstack(
                                            rx.checkbox(
                                                checked=AuthState.settings_compact_mode,
                                                on_change=AuthState.set_settings_compact_mode,
                                            ),
                                            rx.text("Compact mode", size="2"),
                                            spacing="2",
                                            align="center",
                                        ),
                                        spacing="4",
                                        width="100%",
                                        align="start",
                                    ),
                                    width="100%",
                                    size="3",
                                ),
                                columns=rx.breakpoints(initial="1", md="2"),
                                spacing="4",
                                width="100%",
                            ),
                            rx.cond(
                                AuthState.settings_error != "",
                                rx.text(
                                    AuthState.settings_error,
                                    color="red",
                                    size="2",
                                    role="alert",
                                ),
                            ),
                            rx.cond(
                                AuthState.settings_success != "",
                                rx.text(
                                    AuthState.settings_success,
                                    color=success_fg,
                                    size="2",
                                    role="status",
                                ),
                            ),
                            rx.hstack(
                                rx.button(
                                    rx.cond(AuthState.settings_is_submitting, "Saving...", "Save profile"),
                                    type="submit",
                                    loading=AuthState.settings_is_submitting,
                                    disabled=AuthState.settings_is_submitting,
                                    bg=accent_solid,
                                    color="white",
                                    width=rx.breakpoints(initial="100%", sm="auto"),
                                ),
                                rx.button(
                                    "Reset",
                                    type="button",
                                    variant="soft",
                                    on_click=AuthState.load_settings_form,
                                    width=rx.breakpoints(initial="100%", sm="auto"),
                                ),
                                spacing="3",
                                flex_wrap="wrap",
                                width="100%",
                            ),
                            spacing="4",
                            width="100%",
                            align="stretch",
                        ),
                        on_submit=AuthState.save_settings,
                        reset_on_submit=False,
                        width="100%",
                    ),
                    app_footer(),
                    spacing="6",
                    width="100%",
                    padding_y=rx.breakpoints(initial="1rem", md="1.25rem"),
                ),
                size="4",
                width="100%",
                max_width="980px",
                ),
                width="100%",
            ),
            id="main-content",
            tab_index=-1,
            width="100%",
            flex="1",
            outline="none",
        ),
        bg=APP_BACKGROUND,
        color=APP_FOREGROUND,
        min_height="100vh",
        display="flex",
        flex_direction="column",
    )
