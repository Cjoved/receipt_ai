import reflex as rx
from reflex.components.core.upload import upload_file
from reflex.event import EventVar

from receipt_ai.components.ui.buttons import icon_button, panel_action_button
from receipt_ai.components.ui.modals import confirm_modal
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
from receipt_ai.core.upload_constants import (
    FILES_PANEL_UPLOAD_ZONE_ID,
    FILES_UPLOAD_ACCEPT,
    FILES_UPLOAD_ZONE_ID,
)
from receipt_ai.core.theme.tokens import (
    SHADOW_SM,
    accent_muted_fg,
    accent_soft_bg,
    accent_soft_bg_strong,
    border_accent,
    text_primary,
    theme_pair as _mode,
)

_AGRI_ROW_BORDER = _mode("1px solid #bbf7d0", "1px solid #14532d")
from receipt_ai.features.files.state import FilesState

UPLOAD_ZONE_ID = FILES_UPLOAD_ZONE_ID


TABLE_HEADER_BASE_STYLE = {
    "padding": "0.5rem 0.65rem",
    "textAlign": "left",
    "fontSize": "11px",
    "color": _mode("#64748b", "#7f95c1"),
    "fontWeight": "600",
    "letterSpacing": "0.02em",
    "background": _mode("#f1f5fb", "#0c1a33"),
    "borderBottom": f"1px solid {_mode('#d8e3f3', '#1a2e52')}",
}


def delete_confirm_modal() -> rx.Component:
    """Confirmation modal for destructive delete action."""
    return confirm_modal(
        open_state=FilesState.show_delete_confirm,
        title=rx.cond(
            FilesState.selected_child_file_name != "",
            "Delete this file?",
            "Delete this folder?",
        ),
        body=rx.cond(
            FilesState.selected_child_file_name != "",
            rx.vstack(
                rx.text(
                    "This permanently removes the file from storage. Name:",
                    size="2",
                    color=rx.color("gray", 11),
                ),
                rx.text(FilesState.delete_target_label, weight="bold", color=rx.color("gray", 12)),
                spacing="1",
                align="start",
            ),
            rx.vstack(
                rx.text(
                    "This permanently deletes the folder and everything inside it:",
                    size="2",
                    color=rx.color("gray", 11),
                ),
                rx.text(FilesState.delete_target_label, weight="bold", color=rx.color("gray", 12)),
                spacing="1",
                align="start",
            ),
        ),
        confirm_label="Delete",
        on_confirm=FilesState.confirm_delete,
        on_cancel=FilesState.cancel_delete_confirm,
        confirm_color_scheme="red",
    )


def rename_confirm_modal() -> rx.Component:
    """Confirmation modal before applying rename operation."""
    return confirm_modal(
        open_state=FilesState.show_rename_confirm,
        title="Apply rename?",
        body=rx.cond(
            FilesState.selected_child_file_name != "",
            rx.text("Rename file to: ", FilesState.rename_value, color=rx.color("gray", 11)),
            rx.text("Rename folder to: ", FilesState.rename_value, color=rx.color("gray", 11)),
        ),
        confirm_label="Confirm",
        on_confirm=FilesState.save_rename,
        on_cancel=FilesState.cancel_rename_confirm,
    )


def upload_confirm_modal() -> rx.Component:
    """Confirmation modal before uploading staged files (toolbar upload)."""
    return confirm_modal(
        open_state=FilesState.show_upload_confirm,
        title="Upload selected files?",
        body=rx.text(
            "Proceed with uploading staged files to the currently opened folder?",
            color=rx.color("gray", 11),
        ),
        confirm_label="Upload",
        on_confirm=FilesState.upload_files(
            rx.upload_files(
                upload_id=UPLOAD_ZONE_ID,
                on_upload_progress=FilesState.track_upload_progress,
            )
        ),
        on_cancel=FilesState.cancel_upload_confirm,
    )


def panel_drop_confirm_layer() -> rx.Component:
    """Inline confirm (not alert_dialog portal) so Confirm keeps UploadFilesContext for rx.upload_files."""
    return rx.cond(
        FilesState.show_panel_drop_confirm,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.heading("Upload dropped files?", size="4", color=text_primary),
                    rx.text(
                        "Ang mga file na ini-drop ay ia-upload sa folder na ito:",
                        size="2",
                        color=rx.color("gray", 11),
                    ),
                    rx.text(FilesState.expanded_folder_name, weight="bold", color=rx.color("gray", 12)),
                    rx.hstack(
                        rx.button(
                            "Cancel",
                            variant="outline",
                            size="2",
                            on_click=FilesState.cancel_panel_drop_confirm,
                        ),
                        rx.button(
                            "Upload",
                            size="2",
                            color_scheme="green",
                            on_click=FilesState.confirm_panel_drop_upload,
                        ),
                        spacing="3",
                        justify="end",
                        width="100%",
                        margin_top="0.75rem",
                    ),
                    spacing="2",
                    width="100%",
                    align="start",
                ),
                padding="1.25rem",
                border_radius="14px",
                bg=PANEL_BG,
                border=f"1px solid {BORDER_COLOR}",
                box_shadow="0 24px 80px rgba(2, 6, 23, 0.45)",
                max_width="min(420px, 92vw)",
            ),
            position="fixed",
            inset="0",
            z_index="10000",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="1rem",
            background="rgba(2, 6, 23, 0.78)",
            backdrop_filter="blur(4px)",
        ),
        rx.fragment(),
    )


def files_explorer_no_folder_placeholder() -> rx.Component:
    """Main files panel when no folder is selected (startup / collapsed explorer)."""
    return rx.box(
        rx.vstack(
            rx.box(
                rx.icon("folder-open", size=40, color=accent_muted_fg),
                padding="1.25rem",
                border_radius="16px",
                bg=accent_soft_bg,
                border=f"1px solid {border_accent}",
            ),
            rx.heading("Pumili muna ng folder", size="5", color=text_primary),
            rx.text(
                "I-click ang folder sa Explorer sa kaliwa para makita ang mga file, preview, at pag-upload dito.",
                size=TEXT_SIZE_MD,
                color=MUTED_TEXT,
                text_align="center",
                max_width="28rem",
            ),
            rx.text(
                "Tip: Pagkatapos mag-expand, piliin ang file sa grid o list para buksan ang preview.",
                size=TEXT_SIZE_SM,
                color=rx.color("gray", 10),
                text_align="center",
            ),
            spacing="3",
            align="center",
            justify="center",
            width="100%",
            min_height="min(52vh, 420px)",
            class_name="files-no-folder-placeholder",
        ),
        width="100%",
    )


def download_confirm_modal() -> rx.Component:
    """Confirmation before opening a presigned download link."""
    return confirm_modal(
        open_state=FilesState.show_download_confirm,
        title="Download this file?",
        body=rx.vstack(
            rx.text(
                "Your browser will open a secure link to download:",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.text(FilesState.selected_child_file_name, weight="bold", color=rx.color("gray", 12)),
            rx.text(
                "Use your browser’s download dialog to save the file.",
                size="1",
                color=rx.color("gray", 10),
            ),
            spacing="2",
            align="start",
        ),
        confirm_label="Download",
        on_confirm=FilesState.confirm_download,
        on_cancel=FilesState.cancel_download_confirm,
        confirm_color_scheme="green",
    )


def upload_progress_overlay(*, compact: bool = False) -> rx.Component:
    """Spinner + bar while bytes stream to the server (Technical AI upload card)."""
    radius = "14px" if compact else "12px"
    return rx.cond(
        FilesState.is_uploading,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.spinner(size="3"),
                        rx.icon("upload", size=ICON_SIZE_SM, color=accent_muted_fg),
                        spacing="3",
                        justify="center",
                        align="center",
                    ),
                    rx.text(
                        rx.cond(
                            FilesState.upload_progress_pct >= 100,
                            "Processing…",
                            "Uploading…",
                        ),
                        size="2",
                        weight="bold",
                        color=text_primary,
                    ),
                    rx.progress(
                        value=FilesState.upload_progress_pct,
                        max=100,
                        width="100%",
                        color_scheme="green",
                    ),
                    rx.text(FilesState.upload_progress_label, size="1", color=MUTED_TEXT),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                bg=PANEL_BG,
                border=f"1px solid {BORDER_COLOR}",
                border_radius="12px",
                padding="1.5rem",
                min_width="280px",
                box_shadow="0 20px 50px rgba(2, 6, 23, 0.35)",
            ),
            position="absolute",
            inset="0",
            z_index="30",
            border_radius=radius,
            display="flex",
            align_items="center",
            justify_content="center",
            background="rgba(2, 6, 23, 0.45)",
            backdrop_filter="blur(6px)",
        ),
        rx.fragment(),
    )


def upload_overlay() -> rx.Component:
    """Global upload modal shown from the toolbar upload action."""
    return rx.cond(
        FilesState.show_drop_overlay,
        rx.box(
            rx.box(
                upload_progress_overlay(compact=True),
                rx.upload(
                    rx.box(
                        rx.vstack(
                            rx.icon("upload", size=ICON_SIZE_SM),
                            rx.heading("Upload files", size=HEADING_SIZE_SM),
                            rx.text(
                                "Drag files here or click to browse",
                                size=TEXT_SIZE_SM,
                                color=rx.color("gray", 10),
                            ),
                            spacing="1",
                            align="center",
                        ),
                        border=f"2px dashed {rx.color('gray', 7)}",
                        border_radius="12px",
                        padding="1rem",
                        width="100%",
                        min_height="150px",
                        bg=rx.color("gray", 2),
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    id=UPLOAD_ZONE_ID,
                    max_files=5,
                    accept=FILES_UPLOAD_ACCEPT,
                    width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Queue", size=TEXT_SIZE_SM, color=rx.color("gray", 11), weight="medium"),
                        rx.spacer(),
                        rx.button(
                            "Clear all",
                            size="1",
                            variant="ghost",
                            on_click=FilesState.clear_upload_selection,
                        ),
                        width="100%",
                        align="center",
                    ),
                    rx.foreach(
                        rx.selected_files(UPLOAD_ZONE_ID),
                        lambda filename: rx.hstack(
                            rx.text(
                                filename,
                                size=TEXT_SIZE_SM,
                                color=rx.cond(
                                    FilesState.excluded_upload_names.contains(filename),
                                    rx.color("gray", 10),
                                    rx.color("gray", 12),
                                ),
                                text_decoration=rx.cond(
                                    FilesState.excluded_upload_names.contains(filename),
                                    "line-through",
                                    "none",
                                ),
                            ),
                            rx.spacer(),
                            rx.cond(
                                FilesState.excluded_upload_names.contains(filename),
                                rx.button(
                                    "Undo",
                                    size="1",
                                    variant="ghost",
                                    on_click=FilesState.include_upload_file(filename),
                                ),
                                rx.button(
                                    "Skip",
                                    size="1",
                                    variant="ghost",
                                    color_scheme="orange",
                                    on_click=FilesState.exclude_upload_file(filename),
                                ),
                            ),
                            width="100%",
                            align="center",
                            padding_y="0.15rem",
                        ),
                    ),
                    width="100%",
                    spacing="1",
                    max_height="160px",
                    overflow_y="auto",
                    border=f"1px solid {BORDER_COLOR}",
                    border_radius="10px",
                    padding="0.5rem",
                    bg=rx.color("gray", 1),
                ),
                rx.hstack(
                    rx.button(
                        "Upload",
                        on_click=FilesState.request_upload_confirm,
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
                rx.text(
                    "Tip: Select or drag files first, review the queue, then click Upload.",
                    size=TEXT_SIZE_SM,
                    color=rx.color("gray", 10),
                ),
                rx.cond(
                    FilesState.upload_error != "",
                    rx.text(FilesState.upload_error, color="red", size=TEXT_SIZE_SM),
                ),
                upload_confirm_modal(),
                spacing="3",
                width="min(560px, 92vw)",
                bg=PANEL_BG,
                border=f"1px solid {BORDER_COLOR}",
                border_radius="14px",
                padding="1rem",
                box_shadow="0 24px 80px rgba(2, 6, 23, 0.45)",
                position="relative",
            ),
            bg="rgba(2, 6, 23, 0.80)",
            backdrop_filter="blur(2px)",
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
        rx.hstack(
            rx.hstack(
                rx.icon("folder", size=ICON_SIZE_XS, color=accent_muted_fg),
                rx.heading(
                    "Explorer",
                    size="3",
                    weight="bold",
                    color=text_primary,
                    style={"letterSpacing": "-0.02em"},
                ),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.badge("Private", variant="soft", color_scheme="green", size="1"),
                rx.badge("Public", variant="outline", color_scheme="gray", size="1"),
                spacing="1",
            ),
            rx.hstack(
                icon_button("folder-plus", "New folder", on_click=FilesState.open_new_folder_input),
                icon_button(
                    "pencil",
                    "Rename",
                    on_click=FilesState.open_rename_input,
                    disabled=FilesState.expanded_folder_name == "",
                ),
                icon_button(
                    "upload",
                    "Upload",
                    on_click=FilesState.open_upload_input,
                    disabled=FilesState.expanded_folder_name == "",
                ),
                icon_button(
                    "trash",
                    "Delete",
                    on_click=FilesState.request_delete_confirm,
                    disabled=FilesState.expanded_folder_name == "",
                ),
                spacing="3",
            ),
            icon_button("rotate-cw", "Refresh list", on_click=FilesState.load_files),
            width="100%",
            align="center",
            flex_wrap="wrap",
            spacing="2",
        ),

        # Conditional create-folder form.
        rx.cond(
            FilesState.show_new_folder_input,
            rx.vstack(
                rx.hstack(
                    rx.input(
                        placeholder="Folder name",
                        value=FilesState.new_folder_name,
                        on_change=FilesState.set_new_folder_name,
                        size="1",
                    ),
                    rx.button(
                        "Create",
                        size="1",
                        on_click=FilesState.create_new_folder,
                        disabled=rx.cond(FilesState.create_folder_btn_enabled, False, True),
                    ),
                    rx.button("Cancel", size="1", variant="outline", on_click=FilesState.cancel_new_folder),
                    width="100%",
                ),
                rx.cond(
                    FilesState.new_folder_validation_error != "",
                    rx.text(FilesState.new_folder_validation_error, size=TEXT_SIZE_SM, color="orange"),
                ),
                width="100%",
                spacing="1",
            ),
        ),
        # Conditional rename form for selected row.
        rx.cond(
            FilesState.show_rename_input,
            rx.vstack(
                rx.hstack(
                    rx.input(
                        value=FilesState.rename_value,
                        placeholder="New name",
                        on_change=FilesState.set_rename_value,
                        size="1",
                    ),
                    rx.button(
                        "Save",
                        size="1",
                        on_click=FilesState.request_rename_confirm,
                        disabled=rx.cond(FilesState.rename_save_btn_enabled, False, True),
                    ),
                    rx.button("Cancel", size="1", variant="outline", on_click=FilesState.cancel_rename),
                    width="100%",
                ),
                rx.cond(
                    FilesState.rename_validation_error != "",
                    rx.text(FilesState.rename_validation_error, size=TEXT_SIZE_SM, color="orange"),
                ),
                width="100%",
                spacing="1",
            ),
        ),
        # File/folder list section.
        rx.vstack(
            # Loop through file names and render one clickable row per item.
            rx.foreach(
                FilesState.files,
                lambda item: rx.vstack(
                    # Parent row: folder icon and folder name.
                    rx.box(
                        # Row content: icon + name.
                        rx.hstack(
                            rx.icon(
                                tag=rx.cond(
                                    item["name"] == FilesState.expanded_folder_name,
                                    "folder-open",
                                    "folder",
                                ),
                                size=ICON_SIZE_SM,
                                color=accent_muted_fg,
                            ),
                            rx.text(item["name"], size=TEXT_SIZE_MD, color=rx.color("gray", 12)),
                            rx.spacer(),
                            rx.box(width="6px", height="6px", border_radius="999px", bg="#22c55e"),
                            spacing="2",
                            align="center",
                            width="100%",
                        ),
                        padding="0.42rem 0.58rem",
                        border_radius="6px",
                        # Highlight selected row with subtle background.
                        bg=rx.cond(
                            item["name"] == FilesState.expanded_folder_name,
                            accent_soft_bg_strong,
                            "transparent",
                        ),
                        border=rx.cond(
                            item["name"] == FilesState.expanded_folder_name,
                            _AGRI_ROW_BORDER,
                            "1px solid transparent",
                        ),
                        width="100%",
                        cursor="pointer",
                        _hover={"bg": accent_soft_bg},
                        on_click=lambda: FilesState.toggle_folder(item["name"]),
                    ),
                    # Child files: only shown when the folder is expanded.
                    rx.cond(
                        item["name"] == FilesState.expanded_folder_name,
                        rx.vstack(
                            rx.foreach(
                                FilesState.active_folder_children,
                                lambda child: rx.box(
                                    rx.hstack(
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
                                    padding="0.32rem 0.48rem",
                                    border_radius="6px",
                                    cursor="pointer",
                                    width="100%",
                                    bg=rx.cond(
                                        child["name"] == FilesState.selected_child_file_name,
                                        accent_soft_bg_strong,
                                        "transparent",
                                    ),
                                    border=rx.cond(
                                        child["name"] == FilesState.selected_child_file_name,
                                        _AGRI_ROW_BORDER,
                                        "1px solid transparent",
                                    ),
                                    _hover={"bg": accent_soft_bg},
                                    on_click=FilesState.select_child_file(child["name"]),
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
        rename_confirm_modal(),
        delete_confirm_modal(),
        spacing="4",
        width="100%",
        align="start",
        bg=PANEL_BG,
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        padding="0.65rem 0.75rem",
        box_shadow=SHADOW_SM,
    )
def active_child_file_card(child: dict[str, str]) -> rx.Component:
    """Card used in grid view with status + metadata."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(tag=child["icon"], size=ICON_SIZE_MD),
                rx.badge(child["ext"], color_scheme=child["badge"], variant="soft", size="1"),
                rx.spacer(),
                rx.badge(
                    child.get("status", "Completed"),
                    color_scheme="green",
                    variant="soft",
                    size="1",
                ),
                rx.badge(
                    child.get("index_status", "—"),
                    color_scheme=rx.cond(
                        child.get("index_status", "") == "completed",
                        "green",
                        rx.cond(
                            child.get("index_status", "") == "processing",
                            "yellow",
                            rx.cond(
                                child.get("index_status", "") == "failed",
                                "red",
                                "gray",
                            ),
                        ),
                    ),
                    variant="soft",
                    size="1",
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.text(child["name"], size="2", color=rx.color("gray", 12)),
            rx.hstack(
                rx.text(child.get("type", "File"), size="1", color=MUTED_TEXT),
                rx.spacer(),
                rx.text(child.get("size", "-"), size="1", color=MUTED_TEXT),
                width="100%",
                align="center",
            ),
            rx.text(child.get("modified_at", "-"), size="1", color=MUTED_TEXT),
            align="start",
            spacing="2",
        ),
        bg=rx.cond(
            child["name"] == FilesState.selected_child_file_name,
            accent_soft_bg,
            PANEL_BG,
        ),
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        padding="1rem",
        min_width="200px",
        min_height="200px",
        height="100%",
        class_name="files-grid-card",
        cursor="pointer",
        _hover={"border_color": border_accent},
        on_click=FilesState.select_child_file(child["name"]),
    )


def active_child_file_row(child: dict[str, str]) -> rx.Component:
    """Table-like list row aligned with dashboard file explorer style."""
    return rx.el.tr(
        rx.el.td(
            rx.hstack(
                rx.icon(tag=child["icon"], size=ICON_SIZE_SM),
                rx.text(child["name"], size=TEXT_SIZE_MD, color=_mode("#0f172a", "#d8e5ff")),
                spacing="2",
                align="center",
                width="100%",
            ),
            style={"padding": "0.48rem 0.65rem", "whiteSpace": "nowrap"},
        ),
        rx.el.td(child.get("modified_at", "-"), style={"padding": "0.48rem 0.65rem", "whiteSpace": "nowrap", "color": _mode("#64748b", "#8da6d5")}),
        rx.el.td(child.get("type", "File"), style={"padding": "0.48rem 0.65rem", "whiteSpace": "nowrap", "color": _mode("#64748b", "#8da6d5")}),
        rx.el.td(child.get("size", "-"), style={"padding": "0.48rem 0.65rem", "whiteSpace": "nowrap", "color": _mode("#64748b", "#8da6d5")}),
        rx.el.td(
            rx.badge(
                child.get("status", "Completed"),
                color_scheme="green",
                variant="soft",
                size="1",
            ),
            style={"padding": "0.48rem 0.65rem", "whiteSpace": "nowrap"},
        ),
        rx.el.td(
            rx.badge(
                child.get("index_status", "—"),
                color_scheme=rx.cond(
                    child.get("index_status", "") == "completed",
                    "green",
                    rx.cond(
                        child.get("index_status", "") == "processing",
                        "yellow",
                        rx.cond(
                            child.get("index_status", "") == "failed",
                            "red",
                            "gray",
                        ),
                    ),
                ),
                variant="soft",
                size="1",
            ),
            style={"padding": "0.48rem 0.65rem", "whiteSpace": "nowrap"},
        ),
        rx.el.td(
            rx.button(
                rx.icon("trash", size=ICON_SIZE_XS),
                variant="ghost",
                size="1",
                title="Delete file",
                color_scheme="gray",
                on_click=FilesState.request_delete_child_confirm(child["name"]),
            ),
            style={"padding": "0.48rem 0.65rem", "textAlign": "center"},
        ),
        style={
            "borderBottom": f"1px solid {_mode('#d8e3f3', '#183058')}",
            "background": rx.cond(
                child["name"] == FilesState.selected_child_file_name,
                accent_soft_bg,
                "transparent",
            ),
            "cursor": "pointer",
        },
        on_click=FilesState.select_child_file(child["name"]),
    )


def active_children_table() -> rx.Component:
    """Dashboard-style list table with fixed headers and action column."""
    # Reuse one style object so header tweaks happen in one place.
    action_header_style = {**TABLE_HEADER_BASE_STYLE, "textAlign": "center"}
    return rx.box(
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    rx.el.th("NAME", style=TABLE_HEADER_BASE_STYLE),
                    rx.el.th("DATE MODIFIED", style=TABLE_HEADER_BASE_STYLE),
                    rx.el.th("TYPE", style=TABLE_HEADER_BASE_STYLE),
                    rx.el.th("SIZE", style=TABLE_HEADER_BASE_STYLE),
                    rx.el.th("STATUS", style=TABLE_HEADER_BASE_STYLE),
                    rx.el.th("INDEX", style=TABLE_HEADER_BASE_STYLE),
                    rx.el.th("ACTION", style=action_header_style),
                )
            ),
            rx.el.tbody(
                rx.foreach(
                    FilesState.visible_folder_children,
                    lambda child: active_child_file_row(child),
                )
            ),
            style={"width": "100%", "borderCollapse": "collapse"},
        ),
        width="100%",
        overflow_x="auto",
        border=f"1px solid {BORDER_COLOR}",
        border_radius="8px",
        bg=_mode("#ffffff", "#081326"),
    )


def stats_card(title: str, value, hint: str = "") -> rx.Component:
    """Small dashboard metric card for files panel quick insights."""
    return rx.box(
        rx.vstack(
            rx.text(title, size="1", color=MUTED_TEXT),
            rx.text(value, size="4", weight="bold", color=rx.color("gray", 12)),
            rx.cond(
                hint != "",
                rx.text(hint, size="1", color=rx.color("gray", 10)),
            ),
            spacing="1",
            align="start",
        ),
        border=f"1px solid {BORDER_COLOR}",
        border_radius="10px",
        bg=_mode("#ffffff", "#0a162d"),
        padding="0.65rem 0.75rem",
        min_width="170px",
        width="auto",
        flex="1 1 170px",
    )


def file_preview_panel() -> rx.Component:
    """Inline preview for the selected file (only rendered when a file is selected)."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("file-text", size=ICON_SIZE_SM, color=rx.color("gray", 11)),
                rx.text(FilesState.selected_child_file_name, size=TEXT_SIZE_MD, weight="medium"),
                rx.spacer(),
                icon_button(
                    "download",
                    "Download file",
                    on_click=FilesState.request_download_confirm,
                ),
                icon_button(
                    "x",
                    "Close preview",
                    on_click=FilesState.close_preview,
                ),
                width="100%",
                align="center",
            ),
            rx.box(
                rx.cond(
                    FilesState.preview_error != "",
                    rx.text(FilesState.preview_error, color="red", size=TEXT_SIZE_SM),
                    rx.cond(
                        FilesState.preview_display_kind == "image",
                        rx.box(
                            rx.image(
                                src=FilesState.preview_url,
                                width="100%",
                                height="100%",
                                object_fit="contain",
                            ),
                            width="100%",
                            height="100%",
                            overflow="auto",
                        ),
                        rx.cond(
                            FilesState.preview_display_kind == "pdf",
                            rx.el.iframe(
                                src=FilesState.preview_url,
                                width="100%",
                                height="100%",
                                style={"border": "none", "borderRadius": "8px"},
                            ),
                            rx.vstack(
                                rx.cond(
                                    FilesState.preview_display_kind == "csv",
                                    rx.box(
                                        rx.el.table(
                                            rx.el.thead(
                                                rx.el.tr(
                                                    rx.foreach(
                                                        FilesState.preview_csv_headers,
                                                        lambda header: rx.el.th(
                                                            header,
                                                            style={
                                                                "textAlign": "left",
                                                                "padding": "0.5rem 0.6rem",
                                                                "borderBottom": f"1px solid {rx.color('gray', 6)}",
                                                                "position": "sticky",
                                                                "top": "0",
                                                                "background": rx.color("gray", 2),
                                                                "zIndex": "1",
                                                            },
                                                        ),
                                                    )
                                                )
                                            ),
                                            rx.el.tbody(
                                                rx.foreach(
                                                    FilesState.preview_csv_rows,
                                                    lambda row: rx.el.tr(
                                                        rx.foreach(
                                                            row,
                                                            lambda cell: rx.el.td(
                                                                cell,
                                                                style={
                                                                    "padding": "0.45rem 0.6rem",
                                                                    "borderBottom": f"1px solid {rx.color('gray', 4)}",
                                                                    "whiteSpace": "nowrap",
                                                                    "fontFamily": "monospace",
                                                                    "fontSize": "12px",
                                                                },
                                                            ),
                                                        )
                                                    ),
                                                )
                                            ),
                                            style={
                                                "width": "max-content",
                                                "minWidth": "100%",
                                                "borderCollapse": "collapse",
                                            },
                                        ),
                                        width="100%",
                                        height="100%",
                                        overflow="auto",
                                        border=f"1px solid {BORDER_COLOR}",
                                        border_radius="8px",
                                    ),
                                    rx.cond(
                                        FilesState.preview_display_kind == "text",
                                        rx.box(
                                            rx.text(
                                                FilesState.preview_text,
                                                size=TEXT_SIZE_SM,
                                                color=rx.color("gray", 12),
                                                white_space="pre-wrap",
                                                font_family="monospace",
                                            ),
                                            width="100%",
                                            height="100%",
                                            overflow="auto",
                                            border=f"1px solid {BORDER_COLOR}",
                                            border_radius="8px",
                                            padding="0.75rem",
                                        ),
                                        rx.cond(
                                            FilesState.preview_display_kind == "office",
                                            rx.el.iframe(
                                                src=FilesState.preview_embed_url,
                                                width="100%",
                                                height="100%",
                                                style={"border": "none", "borderRadius": "8px"},
                                            ),
                                            rx.vstack(
                                                rx.text(
                                                    "Walang inline preview para sa file type na ito.",
                                                    size=TEXT_SIZE_SM,
                                                    color=MUTED_TEXT,
                                                ),
                                                rx.link(
                                                    "Buksan gamit ang link (bagong tab)",
                                                    href=FilesState.preview_url,
                                                    is_external=True,
                                                    size="2",
                                                ),
                                                spacing="2",
                                                align="start",
                                            ),
                                        ),
                                    ),
                                ),
                                width="100%",
                                height="100%",
                            ),
                        ),
                    ),
                ),
                width="100%",
                flex="1",
                min_height="0",
            ),
            spacing="3",
            width="100%",
            height="100%",
            align="start",
        ),
        download_confirm_modal(),
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        padding="1rem",
        height="calc(100vh - 170px)",
        min_height="560px",
        width="100%",
        bg=PANEL_BG,
        position="relative",
    )


def files_panel() -> rx.Component:
    """Main panel: TA-style drag/drop upload on the panel + list/grid/preview."""
    inner = rx.vstack(
        rx.cond(
            FilesState.upload_error != "",
            rx.text(FilesState.upload_error, color="red", size="2"),
        ),
        # Panel header row.
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("folder-open", size=16, color=accent_muted_fg),
                    rx.heading(
                        rx.cond(
                            FilesState.expanded_folder_name != "",
                            FilesState.expanded_folder_name,
                            "Explorer",
                        ),
                        size="4",
                        weight="bold",
                        style={"letterSpacing": "-0.02em"},
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.text(FilesState.active_child_count_label, size="1", color=_mode("#64748b", "#8da6d5")),
                rx.spacer(),
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
                    spacing="2",
                    class_name="files-view-toggle",
                ),
                width="100%",
                align="center",
            ),
            rx.text(
                rx.cond(FilesState.expanded_folder_name != "", FilesState.visible_child_count_label, ""),
                size="1",
                color=MUTED_TEXT,
            ),
            rx.cond(
                FilesState.expanded_folder_name != "",
                rx.text(
                    "Drop files anywhere on this panel to upload to this folder.",
                    size="1",
                    color=accent_muted_fg,
                ),
            ),
            rx.cond(
                FilesState.expanded_folder_name != "",
                rx.vstack(
                    rx.hstack(
                        rx.input(
                            placeholder="Search files...",
                            value=FilesState.search_query,
                            on_change=FilesState.set_search_query,
                            size="2",
                            width="320px",
                            bg=_mode("#ffffff", "#071126"),
                            border=f"1px solid {BORDER_COLOR}",
                            color=_mode("#0f172a", "#d6deff"),
                            _placeholder={"color": _mode("#94a3b8", "#6f86b3")},
                        ),
                        panel_action_button(
                            "All",
                            active=FilesState.active_type_filter == "all",
                            on_click=lambda: FilesState.set_type_filter("all"),
                        ),
                        panel_action_button(
                            "PDF",
                            active=FilesState.active_type_filter == "pdf",
                            on_click=lambda: FilesState.set_type_filter("pdf"),
                        ),
                        panel_action_button(
                            "Image",
                            active=FilesState.active_type_filter == "image",
                            on_click=lambda: FilesState.set_type_filter("image"),
                        ),
                        panel_action_button(
                            "Doc",
                            active=FilesState.active_type_filter == "doc",
                            on_click=lambda: FilesState.set_type_filter("doc"),
                        ),
                        panel_action_button(
                            "Sheet",
                            active=FilesState.active_type_filter == "sheet",
                            on_click=lambda: FilesState.set_type_filter("sheet"),
                        ),
                        panel_action_button(
                            "Sort: Newest",
                            active=FilesState.sort_mode == "modified_desc",
                            on_click=lambda: FilesState.set_sort_mode("modified_desc"),
                        ),
                        panel_action_button(
                            "Name A-Z",
                            active=FilesState.sort_mode == "name_asc",
                            on_click=lambda: FilesState.set_sort_mode("name_asc"),
                        ),
                        panel_action_button(
                            "Size",
                            active=FilesState.sort_mode == "size_desc",
                            on_click=lambda: FilesState.set_sort_mode("size_desc"),
                        ),
                        rx.cond(
                            FilesState.search_query != "",
                            rx.button(
                                "Clear",
                                variant="ghost",
                                size="1",
                                on_click=FilesState.clear_search_query,
                            ),
                        ),
                        spacing="2",
                        width="100%",
                        align="center",
                        flex_wrap="wrap",
                    ),
                    width="100%",
                    spacing="2",
                ),
            ),
            width="100%",
            spacing="1",
        ),
        # Empty-state when no folder selected (default on load).
        rx.cond(
            FilesState.expanded_folder_name == "",
            files_explorer_no_folder_placeholder(),
        ),
        # Main content area: show either cards/list OR full preview.
            rx.cond(
                FilesState.expanded_folder_name != "",
                rx.cond(
                    FilesState.has_selected_child_file,
                    file_preview_panel(),
                    rx.box(
                        rx.cond(
                            FilesState.view_mode == "grid",
                            rx.box(
                                rx.foreach(
                                    FilesState.visible_folder_children,
                                    lambda child: active_child_file_card(child),
                                ),
                                class_name="files-grid-cards",
                                width="100%",
                            ),
                            active_children_table(),
                        ),
                        width="100%",
                        align_self="start",
                    ),
                ),
            ),
        spacing="4",
        width="100%",
        min_height="calc(100vh - 130px)",
        align="start",
        bg=PANEL_BG,
        border=f"1px solid {BORDER_COLOR}",
        border_radius="12px",
        padding="0.75rem",
        box_shadow=SHADOW_SM,
    )
    return rx.upload.root(
        rx.box(
            inner,
            upload_progress_overlay(compact=False),
            panel_drop_confirm_layer(),
            position="relative",
            width="100%",
        ),
        id=FILES_PANEL_UPLOAD_ZONE_ID,
        width="100%",
        multiple=True,
        max_files=20,
        accept=FILES_UPLOAD_ACCEPT,
        no_click=True,
        on_drop=FilesState.request_panel_drop_confirm,
        drag_active_style={
            "background": "rgba(34, 197, 94, 0.1)",
            "box_shadow": "inset 0 0 0 2px rgba(34, 197, 94, 0.5)",
        },
    )

