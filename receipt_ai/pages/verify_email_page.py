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


def verify_email_page() -> rx.Component:
    return auth_page_shell(
        title="Verify email",
        subtitle="Paste verification token or use token link from email.",
        left_title="Verify your email",
        left_description="Confirm your email to activate account access and secure workspace actions.",
        left_chips=[
            {"label": "Smart Search", "icon_tag": "sparkles"},
            {"label": "Document QA", "icon_tag": "message-square"},
            {"label": "Cloud Storage", "icon_tag": "folder-open"},
        ],
        form_content=rx.form(
            rx.vstack(
                auth_field(
                    "Verification token",
                    auth_text_input(
                        placeholder="Verification token",
                        value=AuthState.verify_token,
                        on_change=AuthState.set_verify_token,
                    ),
                ),
                auth_status_stack(),
                auth_primary_button(
                    rx.cond(AuthState.is_submitting, "Verifying...", "Verify email"),
                    loading=AuthState.is_submitting,
                    disabled=AuthState.is_submitting,
                    button_type="submit",
                ),
                auth_secondary_button(
                    rx.cond(AuthState.is_submitting, "Sending...", "Resend verification email"),
                    on_click=AuthState.resend_verification,
                    disabled=AuthState.is_submitting,
                ),
                auth_secondary_button("Back to login", on_click=AuthState.go_to_login, disabled=AuthState.is_submitting),
                spacing="3",
                width="100%",
                align="stretch",
            ),
            on_submit=AuthState.verify_email,
            reset_on_submit=False,
            width="100%",
        ),
    )
