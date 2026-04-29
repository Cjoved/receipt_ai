import reflex as rx

from receipt_ai.core.constants import APP_BACKGROUND
from receipt_ai.features.auth.state import AuthState

AUTH_LOGO_SRC = "/ChatGPT%20Image%20Apr%2028,%202026,%2003_12_35%20PM.png"
AUTH_BG_VARIANT = "rich"
AUTH_BG_VARIANTS = {
    "subtle": {
        "page_bg": "linear-gradient(150deg, #f3f8f5 0%, #ecf6f1 52%, #e8f3ef 100%)",
        "outside_left_bg": "linear-gradient(140deg, #e8f5ec 0%, #d9f0df 58%, #cde9d6 100%)",
        "outside_left_blobs": "radial-gradient(circle at 6% 10%, rgba(34,197,94,0.18), transparent 32%), radial-gradient(circle at 20% 72%, rgba(22,101,52,0.14), transparent 34%), radial-gradient(circle at 82% 14%, rgba(74,222,128,0.14), transparent 34%), radial-gradient(circle at 72% 88%, rgba(21,128,61,0.12), transparent 36%)",
        "left_overlay": "radial-gradient(circle at 50% 45%, rgba(255,255,255,0.10), transparent 62%)",
        "left_noise_opacity": "0.025",
    },
    "balanced": {
        "page_bg": "linear-gradient(150deg, #eef6f1 0%, #e4f3ea 48%, #dff0e7 100%)",
        "outside_left_bg": "linear-gradient(140deg, #e2f3e8 0%, #d2edd9 58%, #c4e6ce 100%)",
        "outside_left_blobs": "radial-gradient(circle at 5% 10%, rgba(34,197,94,0.20), transparent 32%), radial-gradient(circle at 18% 74%, rgba(21,128,61,0.16), transparent 34%), radial-gradient(circle at 84% 12%, rgba(74,222,128,0.16), transparent 34%), radial-gradient(circle at 76% 90%, rgba(22,101,52,0.14), transparent 36%), radial-gradient(circle at 48% 50%, rgba(255,255,255,0.10), transparent 32%)",
        "left_overlay": "radial-gradient(circle at 50% 45%, rgba(255,255,255,0.14), transparent 60%)",
        "left_noise_opacity": "0.035",
    },
    "rich": {
        "page_bg": "linear-gradient(150deg, #e7f3eb 0%, #dbefdf 46%, #d2ead9 100%)",
        "outside_left_bg": "linear-gradient(140deg, #d9eee3 0%, #c6e4d2 58%, #b5dbc3 100%)",
        "outside_left_blobs": "radial-gradient(ellipse 58% 46% at 8% 10%, rgba(34,197,94,0.34), transparent 66%), radial-gradient(ellipse 52% 40% at 22% 84%, rgba(21,128,61,0.24), transparent 68%), radial-gradient(ellipse 50% 36% at 70% 14%, rgba(74,222,128,0.24), transparent 68%), radial-gradient(ellipse 48% 40% at 66% 88%, rgba(22,101,52,0.24), transparent 70%), radial-gradient(ellipse 42% 34% at 48% 46%, rgba(255,255,255,0.14), transparent 66%), radial-gradient(ellipse 40% 30% at 36% 28%, rgba(110,231,183,0.20), transparent 66%), radial-gradient(ellipse 36% 28% at 54% 72%, rgba(16,185,129,0.16), transparent 68%)",
        "left_overlay": "radial-gradient(circle at 50% 45%, rgba(255,255,255,0.18), transparent 58%)",
        "left_noise_opacity": "0.045",
    },
}
AUTH_INPUT_BASE_STYLE = {
    "width": "100%",
    "height": "2.6rem",
    "border": "none",
    "borderBottom": "1.5px solid #e5e7eb",
    "borderRadius": "0",
    "background": "transparent",
    "color": "#1f2937",
    "paddingLeft": "0.2rem",
    "paddingRight": "0.2rem",
    "_focus": {
        "borderBottomColor": "#1a6b45",
        "boxShadow": "none",
        "outline": "none",
    },
}

AUTH_LEFT_DEFAULT_CHIPS = [
    {"label": "Smart Search", "icon_tag": "sparkles"},
    {"label": "Document QA", "icon_tag": "message-square"},
    {"label": "Cloud Storage", "icon_tag": "folder-open"},
]


def auth_primary_button(label, *, loading: bool = False, disabled: bool = False, button_type: str = "button") -> rx.Component:
    return rx.button(
        label,
        type=button_type,
        width="100%",
        size="3",
        color_scheme="green",
        loading=loading,
        disabled=disabled,
        box_shadow="0 10px 24px rgba(96, 202, 114, 0.28)",
        _hover={
            "transform": "translateY(-1px)",
            "boxShadow": "0 14px 30px rgba(96, 202, 114, 0.32)",
        },
        _active={
            "transform": "translateY(0)",
        },
        transition="all 180ms ease",
    )


def auth_secondary_button(label, *, on_click, disabled: bool = False) -> rx.Component:
    return rx.button(
        label,
        variant="soft",
        type="button",
        on_click=on_click,
        width="100%",
        disabled=disabled,
        bg="rgba(96, 202, 114, 0.14)",
        color=rx.color("green", 11),
        border=f"1px solid {rx.color('green', 6)}",
        _hover={
            "transform": "translateY(-1px)",
            "background": "rgba(96, 202, 114, 0.22)",
        },
        transition="all 180ms ease",
    )


def auth_ghost_button(label, *, on_click, disabled: bool = False) -> rx.Component:
    return rx.button(
        label,
        type="button",
        on_click=on_click,
        disabled=disabled,
        variant="ghost",
        width="100%",
        color=rx.color("green", 11),
        _hover={
            "background": "rgba(96, 202, 114, 0.10)",
        },
        transition="all 180ms ease",
    )


def auth_field(label: str, control: rx.Component) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="2", weight="medium", color="#4b5563"),
        control,
        spacing="1",
        width="100%",
        align="start",
    )


def auth_text_input(
    *,
    value,
    on_change,
    placeholder: str,
    input_type: str = "text",
    on_focus=None,
) -> rx.Component:
    return rx.input(
        type=input_type,
        placeholder=placeholder,
        value=value,
        on_change=on_change,
        on_focus=on_focus,
        **AUTH_INPUT_BASE_STYLE,
    )


def auth_password_field(*, value, on_change, on_focus, show_password, on_toggle) -> rx.Component:
    return auth_field(
        "Password",
        rx.hstack(
            auth_text_input(
                input_type=rx.cond(show_password, "text", "password"),
                placeholder="Enter your password",
                value=value,
                on_change=on_change,
                on_focus=on_focus,
            ),
            rx.button(
                rx.icon(
                    rx.cond(show_password, "eye-off", "eye"),
                    size=16,
                ),
                on_click=on_toggle,
                variant="ghost",
                type="button",
                title=rx.cond(show_password, "Hide password", "Show password"),
                aria_label=rx.cond(show_password, "Hide password", "Show password"),
                aria_pressed=show_password,
                min_width="2.25rem",
                height="2.25rem",
                margin_left="-2.65rem",
                z_index="2",
                color=rx.color("slate", 10),
                _hover={"background": "rgba(22, 163, 74, 0.10)"},
            ),
            width="100%",
            align="center",
            spacing="0",
        ),
    )


def auth_status_stack() -> rx.Component:
    return rx.vstack(
        rx.cond(
            AuthState.auth_error != "",
            rx.hstack(
                rx.icon("triangle-alert", size=16, color=rx.color("tomato", 9)),
                rx.text(AuthState.auth_error, color=rx.color("tomato", 10), size="2"),
                spacing="2",
                align="center",
                width="100%",
                padding="0.6rem 0.7rem",
                border_radius="10px",
                bg=rx.color("tomato", 2),
                border=f"1px solid {rx.color('tomato', 5)}",
            ),
        ),
        rx.cond(
            AuthState.auth_info != "",
            rx.hstack(
                rx.icon("badge-check", size=16, color=rx.color("grass", 9)),
                rx.text(AuthState.auth_info, color=rx.color("grass", 10), size="2"),
                spacing="2",
                align="center",
                width="100%",
                padding="0.6rem 0.7rem",
                border_radius="10px",
                bg=rx.color("grass", 2),
                border=f"1px solid {rx.color('grass', 5)}",
            ),
        ),
        spacing="2",
        width="100%",
        align="stretch",
    )


def LeftBrandingPanel(*, left_title: str, left_description: str, left_chips: list[dict[str, str]]) -> rx.Component:
    bg_tokens = AUTH_BG_VARIANTS.get(AUTH_BG_VARIANT, AUTH_BG_VARIANTS["balanced"])
    return rx.box(
        rx.box(
            position="absolute",
            width="280px",
            height="280px",
            top="-80px",
            right="-60px",
            bg="rgba(255,255,255,0.12)",
            border_radius="60% 40% 30% 70% / 60% 30% 70% 40%",
            style={"animation": "blobMorph 8s ease-in-out infinite"},
        ),
        rx.box(
            position="absolute",
            width="200px",
            height="200px",
            bottom="-50px",
            left="-40px",
            bg="rgba(255,255,255,0.08)",
            border_radius="70% 30% 40% 60% / 50% 60% 40% 50%",
            style={"animation": "blobMorph 11s ease-in-out infinite reverse"},
        ),
        rx.box(
            position="absolute",
            width="120px",
            height="120px",
            top="45%",
            left="15%",
            bg="rgba(255,255,255,0.07)",
            border_radius="40% 60% 70% 30% / 40% 50% 50% 60%",
            style={"animation": "blobMorph 13s ease-in-out infinite"},
        ),
        rx.box(
            position="absolute",
            inset="0",
            bg=bg_tokens["left_overlay"],
            pointer_events="none",
        ),
        rx.box(
            position="absolute",
            inset="0",
            bg="linear-gradient(135deg, rgba(255,255,255,0.06) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.06) 75%, transparent 75%, transparent)",
            background_size="20px 20px",
            opacity=bg_tokens["left_noise_opacity"],
            pointer_events="none",
        ),
        rx.box(
            rx.flex(
                rx.vstack(
                    rx.image(
                        src=AUTH_LOGO_SRC,
                        width=rx.breakpoints(initial="56px", md="72px", lg="84px"),
                        height=rx.breakpoints(initial="56px", md="72px", lg="84px"),
                        border_radius=rx.breakpoints(initial="14px", md="18px", lg="20px"),
                        box_shadow="0 18px 34px rgba(0,0,0,0.24)",
                    ),
                    rx.heading(
                        left_title,
                        color="white",
                        font_size=rx.breakpoints(initial="42px", md="50px", lg="58px"),
                        font_weight="700",
                        letter_spacing="-0.02em",
                        line_height="1.0",
                    ),
                    rx.text(
                        left_description,
                        color="rgba(255,255,255,0.82)",
                        font_size=rx.breakpoints(initial="15px", md="20px", lg="26px"),
                        line_height="1.3",
                        max_width=rx.breakpoints(initial="440px", md="520px", lg="620px"),
                        text_align="center",
                    ),
                    rx.hstack(
                        *[
                            rx.hstack(
                                rx.icon(chip["icon_tag"], size=16, color="rgba(255,255,255,0.90)"),
                                rx.text(
                                    chip["label"],
                                    size="2",
                                    color="rgba(255,255,255,0.92)",
                                    font_weight="500",
                                ),
                                spacing="2",
                                align="center",
                                border="1px solid rgba(255,255,255,0.30)",
                                border_radius="999px",
                                padding="0.36rem 0.78rem",
                                bg="rgba(255,255,255,0.08)",
                            )
                            for chip in left_chips
                        ],
                        width="auto",
                        spacing="3",
                        wrap="wrap",
                        align="center",
                        justify="center",
                    ),
                    spacing=rx.breakpoints(initial="4", md="4", lg="5"),
                    align="center",
                    width="100%",
                    max_width=rx.breakpoints(initial="500px", md="540px", lg="640px"),
                ),
                display="flex",
                direction="column",
                align="center",
                justify="center",
                height="100%",
                width="100%",
            ),
            height="100%",
            min_height="100%",
            width="100%",
            z_index="1",
            position="relative",
            px=rx.breakpoints(initial="1.6rem", md="2.2rem", lg="2.6rem"),
        ),
        width=rx.breakpoints(initial="0", md="58%"),
        min_height="100%",
        height="100%",
        position="relative",
        overflow="hidden",
        bg="linear-gradient(135deg, #60ca72 0%, #1a6b45 100%)",
        display=rx.breakpoints(initial="none", md="block"),
        flex=rx.breakpoints(md="0 0 58%"),
    )


def auth_page_shell(
    *,
    title: str,
    subtitle: str,
    form_content: rx.Component,
    left_title: str = "Receipt AI",
    left_description: str = "AI-powered receipt and document workspace for agriculture teams.",
    left_chips: list[dict[str, str]] | None = None,
) -> rx.Component:
    bg_tokens = AUTH_BG_VARIANTS.get(AUTH_BG_VARIANT, AUTH_BG_VARIANTS["balanced"])
    chips = left_chips or AUTH_LEFT_DEFAULT_CHIPS
    return rx.box(
        rx.el.style(
            """
            @keyframes blobMorph {
              0% { border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; transform: translate(0, 0) rotate(0deg); }
              33% { border-radius: 45% 55% 65% 35% / 40% 60% 40% 60%; transform: translate(8px, -6px) rotate(4deg); }
              66% { border-radius: 55% 45% 35% 65% / 55% 35% 65% 45%; transform: translate(-6px, 8px) rotate(-3deg); }
              100% { border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; transform: translate(0, 0) rotate(0deg); }
            }
            @keyframes fadeInUp {
              from { opacity: 0; transform: translateY(16px); }
              to { opacity: 1; transform: translateY(0); }
            }
            @keyframes authFadeUp {
              from { opacity: 0; transform: translateY(10px); }
              to { opacity: 1; transform: translateY(0); }
            }
            """
        ),
        rx.box(
            position="absolute",
            left="0",
            top="0",
            width="50%",
            height="100%",
            bg=bg_tokens["outside_left_bg"],
            overflow="hidden",
            pointer_events="none",
            z_index="0",
            border_top_right_radius="50% 62%",
            border_bottom_right_radius="56% 74%",
        ),
        rx.box(
            position="absolute",
            left="0",
            top="0",
            width="50%",
            height="100%",
            background_image=bg_tokens["outside_left_blobs"],
            pointer_events="none",
            z_index="0",
            border_top_right_radius="50% 62%",
            border_bottom_right_radius="56% 74%",
        ),
        rx.box(
            rx.image(
                src=AUTH_LOGO_SRC,
                width="100%",
                height="100%",
                object_fit="cover",
                opacity=rx.breakpoints(initial="0.18", md="0.22"),
                filter="drop-shadow(0 12px 30px rgba(21, 128, 61, 0.20))",
            ),
            position="absolute",
            left="0",
            top="0",
            width="50%",
            height="100%",
            overflow="hidden",
            border_top_right_radius="50% 62%",
            border_bottom_right_radius="56% 74%",
            pointer_events="none",
            z_index="0",
        ),
        rx.center(
            rx.box(
                rx.flex(
                    LeftBrandingPanel(
                        left_title=left_title,
                        left_description=left_description,
                        left_chips=chips,
                    ),
                    rx.box(
                        rx.center(
                            rx.vstack(
                                rx.vstack(
                                    rx.hstack(
                                        rx.icon("leaf", size=20, color="#1a6b45"),
                                        rx.heading(
                                            title,
                                            size=rx.breakpoints(initial="5", md="6"),
                                            color="#111827",
                                            letter_spacing="-0.01em",
                                        ),
                                        spacing="2",
                                        align="center",
                                        width="100%",
                                    ),
                                    rx.text(
                                        subtitle,
                                        color="#6b7280",
                                        size="2",
                                        line_height="1.45",
                                    ),
                                    spacing="2",
                                    align="start",
                                    width="100%",
                                ),
                                form_content,
                                width="100%",
                                max_width="390px",
                                spacing="3",
                                animation="authFadeUp 360ms ease-out",
                            ),
                            min_height=rx.breakpoints(initial="auto", md="100%"),
                            width="100%",
                        padding=rx.breakpoints(initial="1.1rem", md="1.6rem", lg="2rem"),
                        ),
                        width=rx.breakpoints(initial="100%", md="42%"),
                        min_height=rx.breakpoints(initial="auto", md="100%"),
                        bg="rgba(255, 255, 255, 0.98)",
                    ),
                    width="100%",
                    height="100%",
                    min_height="100%",
                    direction="row",
                ),
                position="relative",
                width=rx.breakpoints(initial="min(1060px, 94vw)", md="min(1180px, 94vw)"),
                height=rx.breakpoints(initial="auto", md="720px"),
                min_height=rx.breakpoints(initial="auto", md="720px"),
                border_radius=rx.breakpoints(initial="22px", md="24px"),
                overflow="hidden",
                border="none",
                bg="rgba(255,255,255,0.72)",
                box_shadow=rx.breakpoints(initial="none", md="0 24px 80px rgba(15, 23, 42, 0.22)"),
            ),
            width="100%",
            min_height="100vh",
            padding=rx.breakpoints(initial="0.75rem", md="1.25rem"),
            position="relative",
            z_index="1",
        ),
        width="100vw",
        height="100vh",
        min_height="100vh",
        bg=bg_tokens["page_bg"],
        color="#111827",
        position="relative",
        overflow=rx.breakpoints(initial="auto", md="hidden"),
    )
