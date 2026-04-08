import reflex as rx

from receipt_ai.core.constants import APP_BACKGROUND, APP_FOREGROUND
from receipt_ai.features.auth.state import AuthState


def _feature_chip(icon: str, label: str) -> rx.Component:
    return rx.hstack(
        rx.icon(icon, size=14),
        rx.text(label, size="1"),
        spacing="1",
        align="center",
        padding="0.35rem 0.6rem",
        border_radius="9999px",
        bg="rgba(255,255,255,0.08)",
        color="rgba(226, 232, 240, 0.95)",
        border="1px solid rgba(255,255,255,0.12)",
    )


def login_page() -> rx.Component:
    """Split-screen login page inspired by technical_ai design."""
    return rx.box(
        rx.flex(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("leaf", size=28, color="#86efac"),
                        rx.heading("Receipt AI", size="8", color="white"),
                        spacing="3",
                        align="center",
                    ),
                    rx.text(
                        "AI-powered receipt and document workspace for agriculture teams.",
                        color="rgba(226, 232, 240, 0.9)",
                        size="3",
                        max_width="32rem",
                    ),
                    rx.hstack(
                        _feature_chip("search", "Smart Search"),
                        _feature_chip("file-text", "Document QA"),
                        _feature_chip("cloud", "Cloud Storage"),
                        spacing="2",
                        wrap="wrap",
                    ),
                    spacing="5",
                    align="start",
                    width="100%",
                ),
                width="50%",
                min_height="100vh",
                display=rx.breakpoints(initial="none", lg="flex"),
                align_items="center",
                justify_content="center",
                padding="3rem",
                bg="linear-gradient(135deg, #14532d 0%, #166534 45%, #064e3b 100%)",
            ),
            rx.box(
                rx.vstack(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("leaf", size=22, color="#16a34a"),
                            rx.heading("Welcome back", size="6", color=APP_FOREGROUND),
                            spacing="2",
                            align="center",
                        ),
                        rx.text(
                            "Sign in to continue to your Receipt AI workspace.",
                            color=rx.color("gray", 10),
                            size="2",
                        ),
                        spacing="2",
                        width="100%",
                        align="start",
                    ),
                    rx.form(
                        rx.vstack(
                            rx.vstack(
                                rx.text("Email", size="2", weight="medium"),
                                rx.input(
                                    type="email",
                                    placeholder="admin@receipt.ai",
                                    value=AuthState.email,
                                    on_change=AuthState.set_email,
                                    on_focus=AuthState.clear_auth_error,
                                    width="100%",
                                ),
                                spacing="1",
                                width="100%",
                                align="start",
                            ),
                            rx.vstack(
                                rx.text("Password", size="2", weight="medium"),
                                rx.hstack(
                                    rx.input(
                                        type=rx.cond(AuthState.show_password, "text", "password"),
                                        placeholder="Enter your password",
                                        value=AuthState.password,
                                        on_change=AuthState.set_password,
                                        on_focus=AuthState.clear_auth_error,
                                        width="100%",
                                    ),
                                    rx.button(
                                        rx.icon(
                                            rx.cond(AuthState.show_password, "eye-off", "eye"),
                                            size=16,
                                        ),
                                        on_click=AuthState.toggle_show_password,
                                        variant="ghost",
                                        type="button",
                                    ),
                                    width="100%",
                                    align="center",
                                    spacing="1",
                                ),
                                spacing="1",
                                width="100%",
                                align="start",
                            ),
                            rx.cond(
                                AuthState.auth_error != "",
                                rx.text(AuthState.auth_error, color="red", size="2"),
                            ),
                            rx.button(
                                rx.cond(AuthState.is_submitting, "Signing in...", "Sign in"),
                                type="submit",
                                width="100%",
                                size="3",
                                color_scheme="green",
                                loading=AuthState.is_submitting,
                                disabled=AuthState.is_submitting,
                            ),
                            rx.text(
                                "Demo credentials: admin@receipt.ai / admin123",
                                size="1",
                                color=rx.color("gray", 9),
                            ),
                            spacing="3",
                            width="100%",
                            align="start",
                        ),
                        on_submit=AuthState.login,
                        reset_on_submit=False,
                        width="100%",
                    ),
                    spacing="5",
                    width="min(420px, 92vw)",
                    padding="1.75rem",
                    border_radius="14px",
                    border=f"1px solid {rx.color('gray', 6)}",
                    bg=rx.color("gray", 1),
                    box_shadow="0 20px 60px rgba(2, 6, 23, 0.15)",
                ),
                width=rx.breakpoints(initial="100%", lg="50%"),
                min_height="100vh",
                display="flex",
                align_items="center",
                justify_content="center",
                padding="1.25rem",
                bg="linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)",
            ),
            width="100%",
            min_height="100vh",
            direction="row",
        ),
        bg=APP_BACKGROUND,
        color=APP_FOREGROUND,
    )
