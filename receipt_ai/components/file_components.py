import reflex as rx

from receipt_ai.components.ui.buttons import panel_action_button, icon_button
from receipt_ai.core.constants import BORDER_COLOR, MUTED_TEXT, PANEL_BG
from receipt_ai.features.files.service import list_files_payload
from receipt_ai.features.files.state import FilesState

FILES = list_files_payload()


def file_tree() -> rx.Component:
    """Left sidebar: file explorer tree + actions."""
    return rx.vstack(
        # Header row: title + action buttons (new folder, rename, delete).
        rx.hstack(
            rx.heading("My Files", size="4"),
            rx.hstack(
                panel_action_button("+ New", active=True, size="1"),
                icon_button("folder-plus", "New folder", on_click=FilesState.open_new_folder_input),
                icon_button("pencil", "Rename", on_click=FilesState.open_rename_input),
                icon_button("trash", "Delete", on_click=FilesState.delete_file),
                spacing="1",
            ),
            justify="between",
            width="100%",
        ),

        # Inline create-folder form (only shows when state flag is true).
        rx.cond(
            FilesState.show_new_folder_input,
            rx.hstack(
                rx.input(
                    placeholder="Folder name",
                    value=FilesState.new_folder_name,
                    on_change=FilesState.set_new_folder_name,
                    size="1",
                ),
                rx.button("Create", size="1", on_click=FilesState.create_new_folder),
                rx.button("Cancel", size="1", variant="outline", on_click=FilesState.cancel_new_folder),
                width="100%",
            ),
        ),
        # Inline rename form for the currently selected item.
        rx.cond(
            FilesState.show_rename_input,
            rx.hstack(
                rx.input(
                    value=FilesState.rename_value,
                    placeholder="New name",
                    on_change=FilesState.set_rename_value,
                    size="1",
                ),
                rx.button("Save", size="1", on_click=FilesState.save_rename),
                rx.button("Cancel", size="1", variant="outline", on_click=FilesState.cancel_rename),
                width="100%",
            ),
        ),

        # File list: each row is clickable; icon toggles "open" for selected item.
        rx.vstack(
            rx.foreach(
                FilesState.file_names,
                lambda name: rx.box(
                    rx.hstack(
                        rx.icon(
                            tag=rx.cond(
                                name == FilesState.selected_file_name,
                                "folder-open",
                                "folder",
                            ),
                            size=16,
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="0.45rem 0.6rem",
                    border_radius="8px",
                    bg=rx.cond(
                        name == FilesState.selected_file_name,
                        rx.color("gray", 4),
                        "transparent",
                    ),
                    width="100%",
                    cursor="pointer",
                    on_click=lambda: FilesState.select_file(name),
                ),
            ),
            spacing="1",
            width="100%",
            align="start",
        ),
        spacing="4",
        width="100%",
        align="start",
    )

def file_card(title: str, size: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                rx.text("PDF", size="1", color="white"),
                bg="#ef4444",
                border_radius="6px",
                padding="0.15rem 0.4rem",
            ),
            rx.text(title, size="2", color=rx.color("gray", 12)),
            rx.text(size, size="1", color=MUTED_TEXT),
            rx.badge("Completed", color_scheme="green", variant="soft"),
            align="start",
            spacing="2",
        ),
        bg=PANEL_BG,
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        padding="0.75rem",
        min_width="160px",
    )


def files_panel() -> rx.Component:
    cards = FILES[:4]
    return rx.vstack(
        rx.hstack(
            rx.heading("My Files", size="5"),
            rx.spacer(),
            panel_action_button("Grid", active=True),
            panel_action_button("List", active=False),
            width="100%",
        ),
        rx.flex(
            *[file_card(item["name"], item["size"]) for item in cards],
            wrap="wrap",
            spacing="3",
            width="100%",
        ),
        spacing="4",
        width="100%",
        align="start",
    )

