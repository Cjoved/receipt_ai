import reflex as rx


def confirm_modal(
    *,
    open_state,
    title: str,
    body: rx.Component,
    confirm_label: str,
    on_confirm,
    on_cancel,
    confirm_color_scheme: str = "blue",
) -> rx.Component:
    """Reusable confirm modal wrapper based on Reflex alert_dialog."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title(title),
            rx.alert_dialog.description(body),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button("Cancel", variant="outline", on_click=on_cancel),
                ),
                rx.alert_dialog.action(
                    rx.button(confirm_label, color_scheme=confirm_color_scheme, on_click=on_confirm),
                ),
                justify="end",
                width="100%",
                spacing="2",
            ),
        ),
        open=open_state,
    )
