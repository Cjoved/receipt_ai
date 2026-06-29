import reflex as rx

from receipt_ai.components.auth_components import (
    auth_field,
    auth_ghost_button,
    auth_page_shell,
    auth_password_field,
    auth_primary_button,
    auth_status_stack,
    auth_text_input,
)
from receipt_ai.features.auth.state import AuthState


def login_page() -> rx.Component:
    return auth_page_shell(
        title="Welcome back",
        subtitle="Administrator sign-in. Use the account created via seed/bootstrap (admin role).",
        left_title="Receipt AI",
        left_description="Secure sign-in for your agriculture receipt and document workspace.",
        left_chips=[
            {"label": "Smart Search", "icon_tag": "sparkles"},
            {"label": "Document QA", "icon_tag": "message-square"},
            {"label": "Cloud Storage", "icon_tag": "folder-open"},
        ],
        form_content=rx.form(
            rx.vstack(
                auth_field(
                    "Email",
                    auth_text_input(
                        input_type="email",
                        placeholder="admin@receipt.ai",
                        value=AuthState.email,
                        on_change=AuthState.set_email,
                        on_focus=AuthState.clear_auth_error,
                    ),
                ),
                auth_password_field(
                    value=AuthState.password,
                    on_change=AuthState.set_password,
                    on_focus=AuthState.clear_auth_error,
                    show_password=AuthState.show_password,
                    on_toggle=AuthState.toggle_show_password,
                ),
                auth_status_stack(),
                auth_primary_button(
                    rx.cond(AuthState.is_submitting, "Signing in...", "Sign in"),
                    loading=AuthState.is_submitting,
                    disabled=AuthState.is_submitting,
                    button_type="submit",
                ),
                rx.text(
                    "Administrator accounts only. Contact your operator if you need access.",
                    size="1",
                    color=rx.color("gray", 9),
                ),
                rx.vstack(
                    auth_ghost_button(
                        "Forgot password",
                        on_click=AuthState.go_to_forgot_password,
                        disabled=AuthState.is_submitting,
                    ),
                    spacing="2",
                    width="100%",
                    align="stretch",
                ),
                spacing="3",
                width="100%",
                align="stretch",
            ),
            on_submit=AuthState.login,
            reset_on_submit=False,
            width="100%",
        ),
    )