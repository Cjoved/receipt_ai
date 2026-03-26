import reflex as rx

from receipt_ai.components.ui.buttons import icon_button
from receipt_ai.core.constants import (
    BORDER_COLOR,
    HEADING_SIZE_SM,
    ICON_SIZE_MD,
    ICON_SIZE_SM,
    ICON_SIZE_XS,
    MUTED_TEXT,
    PANEL_BG,
    TEXT_SIZE_MD,
    TEXT_SIZE_SM,
)
from receipt_ai.core.upload_constants import FILES_UPLOAD_ZONE_ID
from receipt_ai.features.files.state import FilesState

UPLOAD_ZONE_ID = FILES_UPLOAD_ZONE_ID


def upload_overlay() -> rx.Component:
    """Global upload modal shown from the toolbar upload action."""
    return rx.cond(
        # Show/hide entire modal overlay from state flag.
        FilesState.show_drop_overlay,
        rx.box(
            # Centered modal container on top of darkened full-screen backdrop.
            rx.box(
                # Main upload dropzone: supports drag/drop and click-to-browse.
                rx.upload(
                    rx.box(
                        # Visual content inside the dropzone.
                        rx.vstack(
                            rx.icon("upload", size=ICON_SIZE_MD),
                            rx.heading("Drop files anywhere to upload", size=HEADING_SIZE_SM),
                            rx.text("Drop files here", size=TEXT_SIZE_MD, color=rx.color("gray", 10)),
                            spacing="1",
                            align="center",
                        ),
                        border=f"2px dashed {rx.color('gray', 7)}",
                        border_radius="12px",
                        padding="1.25rem",
                        width="100%",
                        min_height="220px",
                        bg=rx.color("gray", 2),
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    id=UPLOAD_ZONE_ID,
                    on_drop=FilesState.upload_files(
                        rx.upload_files(upload_id=UPLOAD_ZONE_ID)
                    ),
                    max_files=5,
                    accept=".pdf,.jpg,.jpeg,.png,.xlsx,.doc,.docx",
                    width="100%",
                ),
                # Show selected file names before submitting upload.
                rx.foreach(
                    rx.selected_files(UPLOAD_ZONE_ID),
                    lambda filename: rx.text(filename, size=TEXT_SIZE_SM),
                ),
                # Action row for upload and cancel.
                rx.hstack(
                    rx.button(
                        "Upload",
                        on_click=FilesState.upload_files(
                            rx.upload_files(upload_id=UPLOAD_ZONE_ID)
                        ),
                        loading=FilesState.is_uploading,
                        disabled=FilesState.is_uploading,
                        size="2",
                    ),
                    rx.button(
                        "Cancel",
                        variant="outline",
                        on_click=FilesState.cancel_upload,
                        size="2",
                    ),
                    justify="end",
                    width="100%",
                ),
                # Helper note to teach both browse + drag interaction.
                rx.text(
                    "Tip: Click the upload area above to browse, or drag files into it.",
                    size=TEXT_SIZE_SM,
                    color=rx.color("gray", 10),
                ),
                # Inline error message area for failed upload attempts.
                rx.cond(
                    FilesState.upload_error != "",
                    rx.text(FilesState.upload_error, color="red", size=TEXT_SIZE_SM),
                ),
                spacing="2",
                width="min(620px, 92vw)",
            ),
            bg="rgba(2, 6, 23, 0.72)",
            position="fixed",
            inset="0",
            z_index="9999",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="1rem",
        ),
    )


def file_tree() -> rx.Component:
    """Left sidebar: file explorer tree + actions."""
    return rx.vstack(
        # Sidebar header row: title + quick action icons.
        rx.hstack(
            rx.heading("My Files", size="4"),
            # Icon toolbar for create / rename / upload / delete actions.
            rx.hstack(
                icon_button("folder-plus", "New folder", on_click=FilesState.open_new_folder_input),
                icon_button(
                    "pencil",
                    "Rename",
                    on_click=FilesState.open_rename_input,
                    disabled=~FilesState.has_open_folder,
                ),
                icon_button(
                    "upload",
                    "Upload",
                    on_click=FilesState.open_upload_input,
                    disabled=~FilesState.has_open_folder,
                ),
                icon_button(
                    "trash",
                    "Delete",
                    on_click=FilesState.delete_file,
                    disabled=~FilesState.has_open_folder,
                ),
                spacing="3",
            ),
            justify="between",
            width="100%",
        ),

        # Conditional create-folder form.
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
        # Conditional rename form for selected row.
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
        # File/folder list section.
        rx.vstack(
            # Loop through file names and render one clickable row per item.
            rx.foreach(
                FilesState.folder_names,
                lambda name: rx.vstack(
                    # Parent row: folder icon and folder name.
                    rx.box(
                        # Row content: icon + name.
                        rx.hstack(
                            rx.icon(
                                tag=rx.cond(
                                    name == FilesState.expanded_folder_name,
                                    "folder-open",
                                    "folder",
                                ),
                                size=ICON_SIZE_SM,
                                color="#f59e0b",
                            ),
                            rx.text(name, size=TEXT_SIZE_MD, color=rx.color("gray", 12)),
                            spacing="2",
                            align="center",
                        ),
                        padding="0.45rem 0.6rem",
                        border_radius="8px",
                        # Highlight selected row with subtle background.
                        bg=rx.cond(
                            name == FilesState.expanded_folder_name,
                            rx.color("gray", 4),
                            "transparent",
                        ),
                        width="100%",
                        cursor="pointer",
                        on_click=lambda: FilesState.toggle_folder(name),
                    ),
                    # Child files: only shown when the folder is expanded.
                    rx.cond(
                        name == FilesState.expanded_folder_name,
                        rx.vstack(
                            rx.foreach(
                                FilesState.active_folder_children,
                                lambda child: rx.hstack(
                                    rx.icon(
                                        tag=child["icon"],
                                        size=ICON_SIZE_XS,
                                        color=rx.cond(
                                            child["badge"] == "red",
                                            "#ef4444",
                                            rx.cond(
                                                child["badge"] == "purple",
                                                "#a855f7",
                                                rx.cond(
                                                    child["badge"] == "green",
                                                    "#22c55e",
                                                    rx.cond(
                                                        child["badge"] == "blue",
                                                        "#3b82f6",
                                                        rx.cond(
                                                            child["badge"] == "orange",
                                                            "#f97316",
                                                            rx.color("gray", 11),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                    rx.text(child["name"], size=TEXT_SIZE_SM, color=rx.color("gray", 11)),
                                    rx.badge(
                                        child["ext"],
                                        color_scheme=child["badge"],
                                        variant="soft",
                                        size="1",
                                    ),
                                    rx.spacer(),
                                    spacing="2",
                                    align="center",
                                    width="100%",
                                ),
                            ),
                            padding_left="1.8rem",
                            spacing="1",
                            width="100%",
                            align="start",
                        ),
                    ),
                    spacing="1",
                    width="100%",
                    align="start",
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
def active_child_file_card(child: dict[str, str]) -> rx.Component:
    """Card used in the main panel for the active folder's child files."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag=child["icon"], size=ICON_SIZE_MD),
                rx.badge(child["ext"], color_scheme=child["badge"], variant="soft", size="1"),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.text(child["name"], size="2", color=rx.color("gray", 12)),
            rx.text("In folder", size="1", color=MUTED_TEXT),
            align="start",
            spacing="2",
        ),
        bg=PANEL_BG,
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        padding="1rem",
        min_width="200px",
        min_height="200px"
    )


def active_child_file_row(child: dict[str, str]) -> rx.Component:
    """Explorer-style list row used when view mode is list."""
    return rx.hstack(
        rx.hstack(
            rx.icon(tag=child["icon"], size=ICON_SIZE_SM),
            rx.text(child["name"], size=TEXT_SIZE_MD, color=rx.color("gray", 12)),
            spacing="2",
            align="center",
        ),
        rx.spacer(),
        rx.badge(child["ext"], color_scheme=child["badge"], variant="soft", size="1"),
        width="100%",
        padding="0.6rem 0.75rem",
        border=f"1px solid {BORDER_COLOR}",
        border_radius="10px",
        bg=PANEL_BG,
        align="center",
    )


def files_panel() -> rx.Component:
    """Main panel that renders file cards for the selected section."""
    return rx.vstack(
        # Panel header row.
        rx.hstack(
            rx.heading(
                rx.cond(
                    FilesState.expanded_folder_name != "",
                    FilesState.expanded_folder_name,
                    "My Files",
                ),
                size="5",
            ),
            rx.spacer(),
            # View mode toggle: card grid vs list rows.
            rx.hstack(
                icon_button(
                    "layout-grid",
                    "Grid view",
                    on_click=FilesState.set_grid_view,
                    active=FilesState.view_mode == "grid",
                ),
                icon_button(
                    "list",
                    "List view",
                    on_click=FilesState.set_list_view,
                    active=FilesState.view_mode == "list",
                ),
                spacing="4",
            ),
            width="100%",
        ),
        # Empty-state message while no folder is expanded.
        rx.cond(
            FilesState.expanded_folder_name == "",
            rx.text(
                "Open a folder from the left sidebar to view its files.",
                size="2",
                color=MUTED_TEXT,
            ),
        ),
        # Cards for files under the currently expanded folder.
        rx.cond(
            FilesState.expanded_folder_name != "",
            rx.cond(
                FilesState.view_mode == "grid",
                rx.flex(
                    rx.foreach(
                        FilesState.active_folder_children,
                        lambda child: active_child_file_card(child),
                    ),
                    wrap="wrap",
                    spacing="3",
                    width="100%",
                ),
                rx.vstack(
                    rx.foreach(
                        FilesState.active_folder_children,
                        lambda child: active_child_file_row(child),
                    ),
                    spacing="2",
                    width="100%",
                ),
            ),
        ),
        spacing="4",
        width="100%",
        align="start",
    )

