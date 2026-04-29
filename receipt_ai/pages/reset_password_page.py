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


def reset_password_page() -> rx.Component:
    return auth_page_shell(
        title="Reset password",
        subtitle="Use your reset token to set a new password.",
        left_title="Set a new password",
        left_description="Protect your account with a fresh password and continue your workflow.",
        left_chips=[
            {"label": "Smart Search", "icon_tag": "sparkles"},
            {"label": "Document QA", "icon_tag": "message-square"},
            {"label": "Cloud Storage", "icon_tag": "folder-open"},
        ],
        form_content=rx.form(
            rx.vstack(
                auth_field(
                    "Reset token",
                    auth_text_input(
                        placeholder="Reset token",
                        value=AuthState.reset_token,
                        on_change=AuthState.set_reset_token,
                    ),
                ),
                auth_field(
                    "New password",
                    auth_text_input(
                        input_type="password",
                        placeholder="New password",
                        value=AuthState.reset_password,
                        on_change=AuthState.set_reset_password,
                    ),
                ),
                auth_field(
                    "Confirm new password",
                    auth_text_input(
                        input_type="password",
                        placeholder="Confirm new password",
                        value=AuthState.reset_password_confirm,
                        on_change=AuthState.set_reset_password_confirm,
                    ),
                ),
                auth_status_stack(),
                auth_primary_button(
                    rx.cond(AuthState.is_submitting, "Updating password...", "Update password"),
                    loading=AuthState.is_submitting,
                    disabled=AuthState.is_submitting,
                    button_type="submit",
                ),
                auth_secondary_button("Back to login", on_click=AuthState.go_to_login, disabled=AuthState.is_submitting),
                spacing="3",
                width="100%",
                align="stretch",
            ),
            on_submit=AuthState.submit_password_reset,
            reset_on_submit=False,
            width="100%",
        ),
    )
