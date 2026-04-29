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


def forgot_password_page() -> rx.Component:
    return auth_page_shell(
        title="Forgot password",
        subtitle="Enter your email and we will send a reset link.",
        left_title="Recover access",
        left_description="Request a secure reset link and get back to your receipt workspace quickly.",
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
                        placeholder="you@example.com",
                        value=AuthState.forgot_email,
                        on_change=AuthState.set_forgot_email,
                    ),
                ),
                auth_status_stack(),
                auth_primary_button(
                    rx.cond(AuthState.is_submitting, "Sending reset link...", "Send reset link"),
                    loading=AuthState.is_submitting,
                    disabled=AuthState.is_submitting,
                    button_type="submit",
                ),
                auth_secondary_button("Back to login", on_click=AuthState.go_to_login, disabled=AuthState.is_submitting),
                spacing="3",
                width="100%",
                align="stretch",
            ),
            on_submit=AuthState.request_password_reset,
            reset_on_submit=False,
            width="100%",
        ),
    )
