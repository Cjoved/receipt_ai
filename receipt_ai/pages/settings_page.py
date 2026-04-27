import reflex as rx

from receipt_ai.components.app_footer import app_footer
from receipt_ai.components.navigation import top_nav
from receipt_ai.components.skip_link import skip_to_main
from receipt_ai.core.constants import APP_BACKGROUND, APP_FOREGROUND
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
        rx.el.main(
            rx.container(
                rx.vstack(
                    rx.vstack(
                        rx.heading("User Settings", size="7"),
                        rx.text(
                            "Manage account identity and workspace preferences.",
                            size="3",
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
                                        rx.heading("Account", size="5"),
                                        rx.hstack(
                                            rx.badge(AuthState.primary_role, color_scheme="green", variant="soft"),
                                            rx.badge(
                                                rx.cond(AuthState.is_authenticated, "Active", "Inactive"),
                                                color_scheme=rx.cond(
                                                    AuthState.is_authenticated, "grass", "tomato"
                                                ),
                                                variant="soft",
                                            ),
                                            spacing="2",
                                        ),
                                        justify="between",
                                        align="center",
                                        width="100%",
                                    ),
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
                                    _readonly_row("Email", AuthState.email),
                                    spacing="4",
                                    width="100%",
                                    align="start",
                                ),
                                width="100%",
                                size="3",
                            ),
                            rx.card(
                                rx.vstack(
                                    rx.heading("Preferences", size="5"),
                                    rx.vstack(
                                        rx.text("Default page after sign in", size="2", weight="medium"),
                                        rx.hstack(
                                            rx.button(
                                                "Chat",
                                                type="button",
                                                variant=rx.cond(
                                                    AuthState.settings_default_page == "chat", "solid", "soft"
                                                ),
                                                color_scheme="green",
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
                                                    color_scheme="green",
                                                    on_click=AuthState.set_settings_default_page("files"),
                                                ),
                                            ),
                                            spacing="2",
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
                                    color="green",
                                    size="2",
                                    role="status",
                                ),
                            ),
                            rx.hstack(
                                rx.button(
                                    rx.cond(AuthState.settings_is_submitting, "Saving...", "Save settings"),
                                    type="submit",
                                    loading=AuthState.settings_is_submitting,
                                    disabled=AuthState.settings_is_submitting,
                                    color_scheme="green",
                                ),
                                rx.button(
                                    "Reset",
                                    type="button",
                                    variant="soft",
                                    on_click=AuthState.load_settings_form,
                                ),
                                spacing="3",
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
                    padding_y="1.25rem",
                ),
                size="3",
                width="100%",
                max_width="920px",
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
