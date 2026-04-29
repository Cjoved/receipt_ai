import reflex as rx

from receipt_ai.components.auth_components import (
    auth_field,
    auth_page_shell,
    auth_primary_button,
    auth_secondary_button,
    auth_status_stack,
    auth_text_input,
)
from receipt_ai.features.auth.state import AuthState


def register_page() -> rx.Component:
    return auth_page_shell(
        title="Create account",
        subtitle="Register for Receipt AI and verify your email.",
        left_title="Create your account",
        left_description="Set up your team-ready workspace for receipts, files, and AI answers.",
        left_chips=[
            {"label": "Smart Search", "icon_tag": "sparkles"},
            {"label": "Document QA", "icon_tag": "message-square"},
            {"label": "Cloud Storage", "icon_tag": "folder-open"},
        ],
        form_content=rx.form(
            rx.vstack(
                auth_field(
                    "Display name",
                    auth_text_input(
                        placeholder="Display name",
                        value=AuthState.register_display_name,
                        on_change=AuthState.set_register_display_name,
                    ),
                ),
                auth_field(
                    "Email",
                    auth_text_input(
                        input_type="email",
                        placeholder="you@example.com",
                        value=AuthState.register_email,
                        on_change=AuthState.set_register_email,
                    ),
                ),
                auth_field(
                    "Password",
                    auth_text_input(
                        input_type="password",
                        placeholder="Password",
                        value=AuthState.register_password,
                        on_change=AuthState.set_register_password,
                    ),
                ),
                auth_field(
                    "Confirm password",
                    auth_text_input(
                        input_type="password",
                        placeholder="Confirm password",
                        value=AuthState.register_password_confirm,
                        on_change=AuthState.set_register_password_confirm,
                    ),
                ),
                auth_status_stack(),
                auth_primary_button(
                    rx.cond(AuthState.is_submitting, "Creating account...", "Create account"),
                    loading=AuthState.is_submitting,
                    disabled=AuthState.is_submitting,
                    button_type="submit",
                ),
                auth_secondary_button("Back to login", on_click=AuthState.go_to_login, disabled=AuthState.is_submitting),
                spacing="3",
                width="100%",
                align="stretch",
            ),
            on_submit=AuthState.register,
            reset_on_submit=False,
            width="100%",
        ),
    )
