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
    PALETTE_PRIMARY_LIGHT,
    RADIUS_SM,
    SHADOW_SM,
    accent_muted_fg,
    accent_soft_bg,
    accent_soft_bg_strong,
    accent_soft_border,
    border_accent,
    chat_focus_ring,
    chat_input_bg,
    chat_input_focus_border,
    files_panel_card_shadow,
    text_primary,
    theme_pair as _mode,
)

_AGRI_ROW_BORDER = _mode("1px solid #b7eac0", "1px solid #2f5f3b")
from receipt_ai.features.files.state import FilesState

UPLOAD_ZONE_ID = FILES_UPLOAD_ZONE_ID


TABLE_HEADER_BASE_STYLE = {
    "padding": "10px 16px",
    "textAlign": "left",
    "fontSize": "11px",
    "textTransform": "uppercase",
    "color": _mode("#6b7280", "#9ca3af"),
    "fontWeight": "600",
    "letterSpacing": "0.5px",
    "background": _mode("#f9fafb", "#111827"),
    "borderBottom": f"1px solid {_mode('#e5e7eb', '#374151')}",
}


def _files_view_toggle_btn(
    icon: str,
    title: str,
    *,
    active,
    on_click,
) -> rx.Component:
    """Grid/List segment: fill on outer box; soft corners (RADIUS_SM); button is hit-area only."""
    return rx.box(
        rx.button(
            rx.icon(tag=icon, size=ICON_SIZE_SM, color="inherit"),
            variant="ghost",
            size="1",
            on_click=on_click,
            title=title,
            width="100%",
            height="100%",
            min_width="100%",
            min_height="100%",
            padding="0",
            margin="0",
            border="none",
            border_radius=RADIUS_SM,
            cursor="pointer",
            position="relative",
            z_index="1",
            isolation="isolate",
            bg="transparent",
            color=rx.cond(active, "#ffffff", "#9ca3af"),
            box_shadow="none",
            _hover={"background": "transparent"},
            _focus_visible={
                "outline": "2px solid",
                "outline_color": accent_muted_fg,
                "outline_offset": "2px",
            },
        ),
        width="32px",
        height="28px",
        min_width="32px",
        min_height="28px",
        flex_shrink="0",
        flex_grow="0",
        position="relative",
        isolation="isolate",
        border_radius=RADIUS_SM,
        display="flex",
        align_items="center",
        justify_content="center",
        bg=rx.cond(active, "#1a6b45", "transparent"),
        _hover={
            "background": rx.cond(active, "#145535", "rgba(26, 107, 69, 0.1)"),
        },
    )


def _files_panel_view_toggle() -> rx.Component:
    """Pill container: toggles hug content (no dead space); gap keeps highlights apart."""
    return rx.box(
        _files_view_toggle_btn(
            "layout-grid",
            "Grid view",
            active=FilesState.view_mode == "grid",
            on_click=FilesState.set_grid_view,
        ),
        _files_view_toggle_btn(
            "list",
            "List view",
            active=FilesState.view_mode == "list",
            on_click=FilesState.set_list_view,
        ),
        display="flex",
        flex_direction="row",
        align_items="center",
        justify_content="center",
        flex_wrap="nowrap",
        gap="8px",
        padding="6px",
        width="max-content",
        max_width="100%",
        bg=_mode("#f3f4f6", "#1a2332"),
        border_radius="10px",
        border=f"1px solid {_mode('#e5e7eb', '#2d3748')}",
        z_index="2",
    )


def _explorer_legend_pill(label: str) -> rx.Component:
    """Private/Public legend chips (Files spec)."""
    return rx.box(
        rx.text(
            label,
            style={
                "fontSize": "10px",
                "fontWeight": "500",
                "lineHeight": "1.2",
                "color": accent_muted_fg,
            },
        ),
        padding="2px 8px",
        border_radius="20px",
        border=f"1px solid {accent_soft_border}",
        bg=_mode("#f0fdf4", "rgba(96, 202, 114, 0.12)"),
    )

def upload_modal_primary_cta() -> rx.Component:
    """Primary Upload in the modal — static label; counts live in `upload_queue_summary_label` under the row."""
    return rx.button(
        rx.hstack(
            rx.cond(
                FilesState.is_uploading,
                rx.spinner(size="2"),
                rx.fragment(),
            ),
            rx.text("Upload", as_="span", size="2", weight="medium"),
            spacing="2",
            align="center",
        ),
        on_click=FilesState.request_upload_confirm,
        disabled=FilesState.is_uploading,
        size="2",
        variant="solid",
        color_scheme="green",
        min_width="168px",
    )


def _file_type_icon_color(child: dict[str, str]):
    """Map file badge scheme to icon color so list/grid icon tone matches file type."""
    return rx.match(
        child.get("badge", "gray"),
        ("red", _mode("#dc2626", "#f87171")),
        ("blue", _mode("#2563eb", "#60a5fa")),
        ("green", _mode("#16a34a", "#4ade80")),
        ("purple", _mode("#7c3aed", "#c084fc")),
        ("orange", _mode("#ea580c", "#fb923c")),
        _mode("#6b7280", "#9ca3af"),
    )


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
    """Inline confirm layer so UploadFilesContext is preserved for rx.upload_files."""
    return rx.cond(
        FilesState.show_upload_confirm,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.heading("Upload selected files?", size="4", color=text_primary),
                    rx.text(
                        "Proceed with uploading staged files to the currently opened folder?",
                        size="2",
                        color=rx.color("gray", 11),
                    ),
                    rx.hstack(
                        rx.button(
                            "Cancel",
                            variant="outline",
                            on_click=FilesState.cancel_upload_confirm,
                            size="2",
                        ),
                        rx.button(
                            "Upload",
                            color_scheme="green",
                            on_click=FilesState.confirm_upload_from_queue,
                            size="2",
                        ),
                        justify="end",
                        width="100%",
                        spacing="2",
                    ),
                    spacing="3",
                    width="100%",
                ),
                width="min(520px, 92vw)",
                bg=PANEL_BG,
                border=f"1px solid {BORDER_COLOR}",
                border_radius="14px",
                padding="1rem",
                box_shadow="0 24px 80px rgba(2, 6, 23, 0.45)",
            ),
            position="fixed",
            inset="0",
            z_index="10002",
            background="rgba(2, 6, 23, 0.72)",
            display="flex",
            align_items="center",
            justify_content="center",
            padding="1rem",
        ),
        rx.fragment(),
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
                rx.icon("folder-open", size=40, color=PALETTE_PRIMARY_LIGHT),
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


def files_no_results_placeholder() -> rx.Component:
    """Empty-state shown when search/filter returns no matching files."""
    return rx.box(
        rx.vstack(
            rx.box(
                rx.icon("database-zap", size=34, color=accent_muted_fg),
                padding="0.95rem",
                border_radius="14px",
                bg=accent_soft_bg,
                border=f"1px solid {border_accent}",
            ),
            rx.heading("No data was found", size="4", color=text_primary),
            rx.text(
                "Walang tumugmang files sa current search/filter.",
                size=TEXT_SIZE_MD,
                color=MUTED_TEXT,
                text_align="center",
                max_width="28rem",
            ),
            rx.text(
                "Try another search keyword or change active filters.",
                size=TEXT_SIZE_SM,
                color=rx.color("gray", 10),
                text_align="center",
            ),
            spacing="3",
            align="center",
            justify="center",
            width="100%",
            min_height="min(42vh, 340px)",
        ),
        width="100%",
        border=f"1px dashed {BORDER_COLOR}",
        border_radius="12px",
        bg=rx.color("gray", 1),
        padding="1rem",
    )


def files_empty_folder_placeholder() -> rx.Component:
    """Empty-state shown when selected folder has no files yet."""
    return rx.box(
        rx.vstack(
            rx.box(
                rx.icon("folder-open", size=34, color=PALETTE_PRIMARY_LIGHT),
                padding="0.95rem",
                border_radius="14px",
                bg=accent_soft_bg,
                border=f"1px solid {border_accent}",
            ),
            rx.heading("This folder is empty", size="4", color=text_primary),
            rx.text(
                "Wala pang files sa folder na ito.",
                size=TEXT_SIZE_MD,
                color=MUTED_TEXT,
                text_align="center",
                max_width="28rem",
            ),
            rx.text(
                "Mag-upload ng receipt, image, o PDF para mag-start ang extraction.",
                size=TEXT_SIZE_SM,
                color=rx.color("gray", 10),
                text_align="center",
            ),
            spacing="3",
            align="center",
            justify="center",
            width="100%",
            min_height="min(42vh, 340px)",
        ),
        width="100%",
        border=f"1px dashed {BORDER_COLOR}",
        border_radius="12px",
        bg=rx.color("gray", 1),
        padding="1rem",
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
    """Simple blocking upload overlay aligned with app loading patterns."""
    radius = "14px" if compact else "12px"
    return rx.cond(
        FilesState.is_uploading,
        rx.box(
            rx.vstack(
                rx.spinner(size="3"),
                rx.heading("Uploading files...", size="4", color="white"),
                rx.text(
                    rx.cond(
                        FilesState.upload_stage_detail != "",
                        FilesState.upload_stage_detail,
                        "Please wait while we process your files.",
                    ),
                    size="2",
                    color=rx.color("gray", 3),
                    text_align="center",
                    max_width="24rem",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Progress", size="1", color=rx.color("gray", 4)),
                        rx.spacer(),
                        rx.text(FilesState.upload_progress_label, size="1", color=rx.color("gray", 2), weight="bold"),
                        width="100%",
                    ),
                    rx.box(
                        rx.box(
                            height="100%",
                            border_radius="999px",
                            bg=rx.color("green", 8),
                            width=f"{FilesState.upload_progress_pct}%",
                            transition="width 180ms ease",
                        ),
                        width="100%",
                        height="8px",
                        border_radius="999px",
                        bg="rgba(255,255,255,0.20)",
                        overflow="hidden",
                    ),
                    width="min(420px, 88vw)",
                    spacing="1",
                ),
                spacing="3",
                align="center",
            ),
            position="absolute",
            inset="0",
            z_index="30",
            border_radius=radius,
            display="flex",
            align_items="center",
            justify_content="center",
            background="rgba(2, 6, 23, 0.40)",
            backdrop_filter="blur(3px)",
            padding="1rem",
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
                    on_drop=FilesState.cache_upload_previews,
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Queued Files", size=TEXT_SIZE_SM, color=rx.color("gray", 11), weight="medium"),
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
                    rx.box(
                        rx.foreach(
                            FilesState.upload_queue_previews,
                            lambda filename: rx.cond(
                                FilesState.excluded_upload_names.contains(filename["name"]),
                                rx.fragment(),
                                rx.box(
                                    rx.box(
                                        rx.cond(
                                            filename["is_image"] == "1",
                                            rx.cond(
                                                filename["preview_url"] != "",
                                                rx.image(
                                                    src=filename["preview_url"],
                                                    width="100%",
                                                    height="160px",
                                                    object_fit="cover",
                                                    border_radius="12px",
                                                    cursor="pointer",
                                                    on_click=FilesState.open_queued_file_preview(filename["name"]),
                                                    style={"transition": "transform 160ms ease"},
                                                    _hover={"transform": "scale(1.02)"},
                                                ),
                                                rx.box(
                                                    rx.vstack(
                                                        rx.icon("image-off", size=20, color=rx.color("gray", 9)),
                                                        rx.text(
                                                            "Preview unavailable",
                                                            size="1",
                                                            color=rx.color("gray", 10),
                                                        ),
                                                        spacing="1",
                                                        align="center",
                                                    ),
                                                    width="100%",
                                                    height="160px",
                                                    border_radius="12px",
                                                    border=f"1px dashed {rx.color('gray', 6)}",
                                                    bg=rx.color("gray", 2),
                                                    display="flex",
                                                    align_items="center",
                                                    justify_content="center",
                                                ),
                                            ),
                                            rx.cond(
                                                filename["preview_kind"] == "pdf",
                                                rx.box(
                                                    rx.vstack(
                                                        rx.icon("file-text", size=22, color=accent_muted_fg),
                                                        rx.text("Preview PDF", size="1", color=rx.color("gray", 10)),
                                                        spacing="1",
                                                        align="center",
                                                    ),
                                                    width="100%",
                                                    height="160px",
                                                    border_radius="12px",
                                                    border=f"1px solid {BORDER_COLOR}",
                                                    bg=rx.color("gray", 2),
                                                    display="flex",
                                                    align_items="center",
                                                    justify_content="center",
                                                    cursor=rx.cond(filename["preview_url"] != "", "pointer", "default"),
                                                    on_click=FilesState.open_queued_file_preview(filename["name"]),
                                                ),
                                                rx.cond(
                                                    filename["preview_kind"] == "pdf_image",
                                                    rx.box(
                                                        rx.vstack(
                                                            rx.icon("file-text", size=22, color=accent_muted_fg),
                                                            rx.text("Preview PDF", size="1", color=rx.color("gray", 10)),
                                                            spacing="1",
                                                            align="center",
                                                        ),
                                                        width="100%",
                                                        height="160px",
                                                        border_radius="12px",
                                                        border=f"1px solid {BORDER_COLOR}",
                                                        bg=rx.color("gray", 2),
                                                        display="flex",
                                                        align_items="center",
                                                        justify_content="center",
                                                        cursor=rx.cond(filename["preview_url"] != "", "pointer", "default"),
                                                        on_click=FilesState.open_queued_file_preview(filename["name"]),
                                                    ),
                                                    rx.box(
                                                        rx.icon("file-text", size=22, color=accent_muted_fg),
                                                        width="100%",
                                                        height="160px",
                                                        border_radius="12px",
                                                        border=f"1px solid {BORDER_COLOR}",
                                                        bg=rx.color("gray", 2),
                                                        display="flex",
                                                        align_items="center",
                                                        justify_content="center",
                                                    ),
                                                ),
                                            ),
                                        ),
                                        rx.button(
                                            rx.icon("x", size=14),
                                            size="1",
                                            color_scheme="red",
                                            variant="solid",
                                            on_click=FilesState.exclude_upload_file(filename["name"]),
                                            title=f"Remove {filename['name']} from queue",
                                            aria_label=f"Remove {filename['name']} from queue",
                                            position="absolute",
                                            top="0.4rem",
                                            right="0.4rem",
                                            z_index="3",
                                            border_radius="9999px",
                                            min_width="32px",
                                            min_height="32px",
                                        ),
                                        position="relative",
                                        width="100%",
                                    ),
                                    rx.text(
                                        filename["name"],
                                        size="1",
                                        color=rx.color("gray", 12),
                                        max_width="100%",
                                        style={
                                            "display": "-webkit-box",
                                            "-webkitLineClamp": "2",
                                            "-webkitBoxOrient": "vertical",
                                            "overflow": "hidden",
                                            "lineHeight": "1.2",
                                            "minHeight": "2.4em",
                                        },
                                    ),
                                    rx.text(
                                        rx.cond(
                                            filename["is_image"] == "1",
                                            "Image • Queued",
                                            rx.cond(
                                                filename["preview_kind"] == "pdf",
                                                "PDF • Queued",
                                                rx.cond(
                                                    filename["preview_kind"] == "pdf_image",
                                                    "PDF • Queued",
                                                    "File • Queued",
                                                ),
                                            ),
                                        ),
                                        size="1",
                                        color=rx.color("gray", 10),
                                    ),
                                    width="100%",
                                    padding="0.35rem",
                                    border=f"1px solid {BORDER_COLOR}",
                                    border_radius="12px",
                                    bg=rx.color("gray", 1),
                                ),
                            ),
                        ),
                        width="100%",
                        display="grid",
                        grid_template_columns="repeat(auto-fill, minmax(180px, 1fr))",
                        gap="0.55rem",
                    ),
                    rx.cond(
                        FilesState.excluded_upload_names != [],
                        rx.vstack(
                            rx.hstack(
                                rx.text("Removed", size="1", color=rx.color("gray", 10), weight="medium"),
                                rx.spacer(),
                                rx.button(
                                    "Undo all",
                                    size="1",
                                    variant="ghost",
                                    on_click=FilesState.clear_removed_upload_files,
                                ),
                                width="100%",
                                align="center",
                            ),
                            rx.foreach(
                                FilesState.excluded_upload_names,
                                lambda filename: rx.hstack(
                                    rx.text(filename, size="1", color=rx.color("gray", 10), max_width="280px"),
                                    rx.spacer(),
                                    rx.button(
                                        "Undo",
                                        size="1",
                                        variant="ghost",
                                        on_click=FilesState.include_upload_file(filename),
                                    ),
                                    width="100%",
                                    align="center",
                                ),
                            ),
                            width="100%",
                            spacing="1",
                        ),
                    ),
                    rx.cond(
                        FilesState.upload_queue_previews == [],
                        rx.vstack(
                            rx.foreach(
                                rx.selected_files(UPLOAD_ZONE_ID),
                                lambda fallback_name: rx.text(
                                    fallback_name,
                                    size="1",
                                    color=rx.color("gray", 11),
                                ),
                            ),
                            rx.text(
                                "Preview loading... kapag image ito, lalabas dito ang thumbnail.",
                                size="1",
                                color=rx.color("gray", 10),
                            ),
                            width="100%",
                            spacing="1",
                        ),
                    ),
                    width="100%",
                    spacing="1",
                    max_height="360px",
                    overflow_y="auto",
                    border=f"1px solid {BORDER_COLOR}",
                    border_radius="10px",
                    padding="0.5rem",
                    bg=rx.color("gray", 1),
                ),
                rx.cond(
                    FilesState.show_queued_preview,
                    rx.box(
                        rx.box(
                            rx.hstack(
                                rx.text(FilesState.queued_preview_name, weight="bold", color=text_primary, size="2"),
                                rx.spacer(),
                                rx.button(
                                    rx.icon("x", size=16),
                                    size="1",
                                    variant="soft",
                                    on_click=FilesState.close_queued_image_preview,
                                ),
                                width="100%",
                                align="center",
                            ),
                            rx.cond(
                                FilesState.queued_preview_kind == "pdf",
                                rx.vstack(
                                    rx.el.embed(
                                        src=FilesState.queued_preview_url,
                                        type="application/pdf",
                                        width="min(84vw, 980px)",
                                        height="78vh",
                                        style={
                                            "border": f"1px solid {BORDER_COLOR}",
                                            "borderRadius": "12px",
                                            "background": rx.color("gray", 1),
                                        },
                                    ),
                                    rx.link(
                                        "Open PDF in new tab",
                                        href=FilesState.queued_preview_url,
                                        target="_blank",
                                        color=accent_muted_fg,
                                        underline="always",
                                    ),
                                    width="min(86vw, 980px)",
                                    spacing="2",
                                    align="start",
                                ),
                                rx.cond(
                                    FilesState.queued_preview_kind == "pdf_image",
                                    rx.box(
                                        rx.vstack(
                                            rx.foreach(
                                                FilesState.queued_preview_pages,
                                                lambda page_src: rx.image(
                                                    src=page_src,
                                                    width="100%",
                                                    object_fit="contain",
                                                    border_radius="10px",
                                                    border=f"1px solid {BORDER_COLOR}",
                                                    bg=rx.color("gray", 1),
                                                ),
                                            ),
                                            width="100%",
                                            spacing="2",
                                            align="stretch",
                                        ),
                                        width="min(86vw, 980px)",
                                        max_height="80vh",
                                        overflow_y="auto",
                                        border=f"1px solid {BORDER_COLOR}",
                                        border_radius="12px",
                                        padding="0.5rem",
                                        bg=rx.color("gray", 2),
                                    ),
                                    rx.image(
                                        src=FilesState.queued_preview_url,
                                        width="min(80vw, 900px)",
                                        max_height="80vh",
                                        object_fit="contain",
                                        border_radius="12px",
                                        border=f"1px solid {BORDER_COLOR}",
                                        bg=rx.color("gray", 1),
                                    ),
                                ),
                            ),
                            spacing="2",
                            width="min(86vw, 940px)",
                        ),
                        position="fixed",
                        inset="0",
                        z_index="10001",
                        background="rgba(2, 6, 23, 0.80)",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        padding="1rem",
                    ),
                ),
                rx.vstack(
                    rx.hstack(
                        upload_modal_primary_cta(),
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
                        FilesState.upload_queue_summary_label,
                        size="1",
                        color=MUTED_TEXT,
                        width="100%",
                        text_align="end",
                    ),
                    spacing="1",
                    width="100%",
                    align="end",
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
                rx.text(
                    "Explorer",
                    style={
                        "fontSize": "13px",
                        "fontWeight": "600",
                        "color": text_primary,
                        "letterSpacing": "-0.02em",
                    },
                ),
                spacing="2",
                align="center",
            ),
            rx.button(
                rx.icon("x", size=14, color="inherit"),
                variant="ghost",
                size="1",
                on_click=FilesState.close_sidebar,
                display=["flex", "none", "none", "none"],
                title="Close explorer",
            ),
            rx.spacer(),
            rx.hstack(
                _explorer_legend_pill("Private"),
                _explorer_legend_pill("Public"),
                spacing="1",
            ),
            rx.hstack(
                icon_button(
                    "folder-plus",
                    "New folder",
                    on_click=FilesState.open_new_folder_input,
                    variant="explorer",
                ),
                icon_button(
                    "pencil",
                    "Rename",
                    on_click=FilesState.open_rename_input,
                    disabled=FilesState.expanded_folder_name == "",
                    variant="explorer",
                ),
                icon_button(
                    "upload",
                    "Upload",
                    on_click=FilesState.open_upload_input,
                    disabled=FilesState.expanded_folder_name == "",
                    variant="explorer",
                ),
                icon_button(
                    "trash",
                    "Delete",
                    on_click=FilesState.request_delete_confirm,
                    disabled=FilesState.expanded_folder_name == "",
                    variant="explorer",
                ),
                spacing="3",
            ),
            icon_button("rotate-cw", "Refresh list", on_click=FilesState.load_files, variant="explorer"),
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
                            rx.cond(
                                (FilesState.show_rename_input)
                                & (FilesState.selected_child_file_name == "")
                                & (item["name"] == FilesState.expanded_folder_name),
                                rx.hstack(
                                    rx.input(
                                        value=FilesState.rename_value,
                                        on_change=FilesState.set_rename_value,
                                        size="1",
                                        width="100%",
                                        auto_focus=True,
                                    ),
                                    rx.button(
                                        "Save",
                                        size="1",
                                        on_click=FilesState.request_rename_confirm,
                                        disabled=rx.cond(FilesState.rename_save_btn_enabled, False, True),
                                    ),
                                    rx.button(
                                        "Cancel",
                                        size="1",
                                        variant="outline",
                                        on_click=FilesState.cancel_rename,
                                    ),
                                    spacing="2",
                                    align="center",
                                    width="100%",
                                ),
                                rx.text(
                                    item["name"],
                                    style={
                                        "fontSize": "13px",
                                        "fontWeight": rx.cond(
                                            item["name"] == FilesState.expanded_folder_name,
                                            "500",
                                            "400",
                                        ),
                                        "color": rx.cond(
                                            item["name"] == FilesState.expanded_folder_name,
                                            accent_muted_fg,
                                            _mode("#374151", "#d1d5db"),
                                        ),
                                    },
                                ),
                            ),
                            rx.spacer(),
                            rx.box(width="6px", height="6px", border_radius="999px", bg="#60ca72"),
                            spacing="2",
                            align="center",
                            width="100%",
                        ),
                        padding_top="8px",
                        padding_bottom="8px",
                        padding_right="12px",
                        padding_left=rx.cond(
                            item["name"] == FilesState.expanded_folder_name,
                            "9px",
                            "12px",
                        ),
                        border_radius="8px",
                        border_left=rx.cond(
                            item["name"] == FilesState.expanded_folder_name,
                            "3px solid #1a6b45",
                            "3px solid transparent",
                        ),
                        bg=rx.cond(
                            item["name"] == FilesState.expanded_folder_name,
                            _mode("#f0fdf4", "rgba(26, 107, 69, 0.22)"),
                            "transparent",
                        ),
                        width="100%",
                        cursor="pointer",
                        _hover={
                            "background": rx.cond(
                                item["name"] == FilesState.expanded_folder_name,
                                _mode("#f0fdf4", "rgba(26, 107, 69, 0.22)"),
                                _mode("#f0fdf4", "rgba(96, 202, 114, 0.1)"),
                            ),
                        },
                        on_click=rx.cond(
                            (FilesState.show_rename_input)
                            & (FilesState.selected_child_file_name == "")
                            & (item["name"] == FilesState.expanded_folder_name),
                            None,
                            FilesState.toggle_folder(item["name"]),
                        ),
                    ),
                    rx.cond(
                        (FilesState.show_rename_input)
                        & (FilesState.selected_child_file_name == "")
                        & (item["name"] == FilesState.expanded_folder_name)
                        & (FilesState.rename_validation_error != ""),
                        rx.text(
                            FilesState.rename_validation_error,
                            size=TEXT_SIZE_SM,
                            color="orange",
                            width="100%",
                            padding_left="0.4rem",
                        ),
                    ),
                    # Child files: only shown when the folder is expanded.
                    rx.cond(
                        item["name"] == FilesState.expanded_folder_name,
                        rx.vstack(
                            rx.foreach(
                                FilesState.active_folder_children,
                                lambda child: rx.box(
                                    rx.vstack(
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
                                                            "#60ca72",
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
                                            rx.cond(
                                                (FilesState.show_rename_input)
                                                & (FilesState.selected_child_file_name == child["name"]),
                                                rx.hstack(
                                                    rx.input(
                                                        value=FilesState.rename_value,
                                                        on_change=FilesState.set_rename_value,
                                                        size="1",
                                                        width="100%",
                                                        auto_focus=True,
                                                    ),
                                                    rx.button(
                                                        "Save",
                                                        size="1",
                                                        on_click=FilesState.request_rename_confirm,
                                                        disabled=rx.cond(FilesState.rename_save_btn_enabled, False, True),
                                                    ),
                                                    rx.button(
                                                        "Cancel",
                                                        size="1",
                                                        variant="outline",
                                                        on_click=FilesState.cancel_rename,
                                                    ),
                                                    spacing="2",
                                                    align="center",
                                                    width="100%",
                                                ),
                                                rx.hstack(
                                                    rx.text(child["name"], size=TEXT_SIZE_SM, color=rx.color("gray", 11)),
                                                    rx.badge(
                                                        child["ext"],
                                                        color_scheme=child["badge"],
                                                        variant="soft",
                                                        size="1",
                                                    ),
                                                    spacing="2",
                                                    align="center",
                                                ),
                                            ),
                                            rx.spacer(),
                                            spacing="2",
                                            align="center",
                                            width="100%",
                                        ),
                                        rx.cond(
                                            (FilesState.show_rename_input)
                                            & (FilesState.selected_child_file_name == child["name"])
                                            & (FilesState.rename_validation_error != ""),
                                            rx.text(
                                                FilesState.rename_validation_error,
                                                size=TEXT_SIZE_SM,
                                                color="orange",
                                                width="100%",
                                                padding_left="1.35rem",
                                            ),
                                        ),
                                        spacing="2",
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
                                    on_click=rx.cond(
                                        (FilesState.show_rename_input)
                                        & (FilesState.selected_child_file_name == child["name"]),
                                        None,
                                        FilesState.select_child_file(child["name"]),
                                    ),
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
        border=f"1px solid {_mode('#e5e7eb', '#374151')}",
        border_radius="12px",
        padding="12px",
        box_shadow=SHADOW_SM,
    )
def active_child_file_card(child: dict[str, str]) -> rx.Component:
    """Card used in grid view: badges wrap (no overflow); filename ellipsis; even vertical rhythm."""
    badge_radius = "full"
    file_icon_color = _file_type_icon_color(child)
    return rx.box(
        rx.vstack(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag=child["icon"], size=ICON_SIZE_MD, color=file_icon_color),
                    rx.badge(
                        child["ext"],
                        color_scheme=child["badge"],
                        variant="soft",
                        size="1",
                        radius=badge_radius,
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.hstack(
                    rx.badge(
                        child.get("status", "Completed"),
                        color_scheme="green",
                        variant="soft",
                        size="1",
                        radius=badge_radius,
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
                        radius=badge_radius,
                        class_name="files-grid-index-badge",
                    ),
                    spacing="2",
                    align="center",
                    flex_wrap="wrap",
                    width="100%",
                ),
                spacing="2",
                align="start",
                width="100%",
                min_width="0",
            ),
            rx.text(
                child["name"],
                size="2",
                color=rx.color("gray", 12),
                width="100%",
                style={
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                    "minWidth": 0,
                },
            ),
            rx.hstack(
                rx.text(child.get("type", "File"), size="1", color=MUTED_TEXT),
                rx.spacer(),
                rx.text(child.get("size", "-"), size="1", color=MUTED_TEXT),
                width="100%",
                align="center",
                min_width="0",
            ),
            rx.text(child.get("uploaded_at", child.get("modified_at", "-")), size="1", color=MUTED_TEXT),
            align="start",
            spacing="2",
            width="100%",
            min_width="0",
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
        width="100%",
        max_width="100%",
        overflow="hidden",
        class_name="files-grid-card",
        cursor="pointer",
        _hover={"border_color": border_accent},
        on_click=FilesState.select_child_file(child["name"]),
    )


def _table_meta_cell(content, *, display=None) -> rx.Component:
    return rx.el.td(
        content,
        style={
            "padding": "14px 16px",
            "whiteSpace": "nowrap",
            "fontSize": "13px",
            "color": _mode("#374151", "#d1d5db"),
            "textAlign": "left",
            "verticalAlign": "middle",
        },
        display=display,
    )


def _index_status_pill(child: dict[str, str]) -> rx.Component:
    """Status chip for INDEX column — width hugs label (avoids stretched pill in wide <td>)."""
    idx = child.get("index_status", "—")
    pill_common = {"width": "max-content", "max_width": "100%"}
    return rx.cond(
        child.get("index_status", "") == "completed",
        rx.box(
            rx.text(idx, style={"fontSize": "11px", "fontWeight": "500", "color": accent_muted_fg}),
            padding="3px 10px",
            border_radius="20px",
            border=f"1px solid {accent_soft_border}",
            bg=_mode("#f0fdf4", "rgba(96, 202, 114, 0.14)"),
            **pill_common,
        ),
        rx.cond(
            child.get("index_status", "") == "processing",
            rx.box(
                rx.text(idx, style={"fontSize": "11px", "fontWeight": "500", "color": _mode("#92400e", "#fcd34d")}),
                padding="3px 10px",
                border_radius="20px",
                border=f"1px solid {_mode('#fde68a', '#78350f')}",
                bg=_mode("#fffbeb", "rgba(251, 191, 36, 0.12)"),
                **pill_common,
            ),
            rx.cond(
                child.get("index_status", "") == "failed",
                rx.box(
                    rx.text(idx, style={"fontSize": "11px", "fontWeight": "500", "color": _mode("#b91c1c", "#fca5a5")}),
                    padding="3px 10px",
                    border_radius="20px",
                    border=f"1px solid {_mode('#fecaca', '#7f1d1d')}",
                    bg=_mode("#fef2f2", "rgba(248, 113, 113, 0.12)"),
                    **pill_common,
                ),
                rx.box(
                    rx.text(idx, style={"fontSize": "11px", "fontWeight": "500", "color": _mode("#374151", "#9ca3af")}),
                    padding="3px 10px",
                    border_radius="20px",
                    border=f"1px solid {BORDER_COLOR}",
                    bg=_mode("#f9fafb", "#1f2937"),
                    **pill_common,
                ),
            ),
        ),
    )


def active_child_file_row(child: dict[str, str]) -> rx.Component:
    """Table-like list row (Files spec: hover, pills, delete)."""
    cell_pad = {"padding": "14px 16px", "whiteSpace": "nowrap", "verticalAlign": "middle"}
    icon_cell_pad = {**cell_pad, "textAlign": "center", "width": "52px", "paddingLeft": "8px", "paddingRight": "8px"}
    date_display = ["none", "none", "table-cell", "table-cell"]
    type_display = ["none", "table-cell", "table-cell", "table-cell"]
    size_display = ["none", "none", "table-cell", "table-cell"]
    index_display = ["none", "none", "none", "table-cell"]
    status_label = child.get("status", "Completed")
    file_icon_color = _file_type_icon_color(child)
    return rx.el.tr(
        rx.el.td(
            rx.icon(tag=child["icon"], size=ICON_SIZE_MD, color=file_icon_color),
            style=icon_cell_pad,
        ),
        rx.el.td(
            rx.tooltip(
                rx.text(
                    child["name"],
                    style={
                        "fontSize": "13px",
                        "fontWeight": "500",
                        "color": _mode("#111827", "#f9fafb"),
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                        "display": "block",
                    },
                ),
                content=child["name"],
                delay_duration=300,
            ),
            style={**cell_pad, "textAlign": "left", "overflow": "hidden"},
            width=["auto", "auto", "300px", "400px"],
            max_width=["160px", "200px", "300px", "400px"],
        ),
        _table_meta_cell(child.get("uploaded_at", child.get("modified_at", "-")), display=date_display),
        rx.el.td(
            rx.badge(
                child["ext"],
                color_scheme=child["badge"],
                variant="soft",
                size="1",
                radius="full",
            ),
            style={**cell_pad, "textAlign": "left"},
            display=type_display,
        ),
        _table_meta_cell(child.get("size", "-"), display=size_display),
        rx.el.td(
            rx.box(
                rx.text(
                    status_label,
                    style={"fontSize": "11px", "fontWeight": "500", "color": _mode("#065f46", "#a7e8b2")},
                ),
                padding="3px 10px",
                border_radius="20px",
                bg=_mode("#d1fae5", "rgba(34, 197, 94, 0.18)"),
                width="max-content",
                max_width="100%",
            ),
            style={**cell_pad, "textAlign": "left"},
        ),
        rx.el.td(
            _index_status_pill(child),
            style={**cell_pad, "textAlign": "left"},
            display=index_display,
        ),
        rx.el.td(
            rx.button(
                rx.icon("trash", size=ICON_SIZE_XS, color="inherit"),
                variant="ghost",
                size="1",
                title="Delete file",
                on_click=FilesState.request_delete_child_confirm(child["name"]),
                min_width="28px",
                min_height="28px",
                border_radius="6px",
                color=accent_muted_fg,
                bg="transparent",
                _hover={
                    "color": "#ef4444",
                    "background": _mode("#fef2f2", "rgba(248, 113, 113, 0.15)"),
                },
                _focus_visible={
                    "outline": "2px solid",
                    "outline_color": accent_muted_fg,
                    "outline_offset": "1px",
                },
            ),
            style={**cell_pad, "textAlign": "center"},
        ),
        class_name="files-table-row",
        style={
            "borderBottom": f"1px solid {_mode('#f3f4f6', '#1f2937')}",
            "background": rx.cond(
                child["name"] == FilesState.selected_child_file_name,
                _mode("#f0fdf4", "rgba(96, 202, 114, 0.12)"),
                "transparent",
            ),
            "cursor": "pointer",
        },
        on_click=FilesState.select_child_file(child["name"]),
    )


def active_children_table() -> rx.Component:
    """Dashboard-style list table with fixed headers and action column."""
    # Reuse one style object so header tweaks happen in one place.
    date_display = ["none", "none", "table-cell", "table-cell"]
    type_display = ["none", "table-cell", "table-cell", "table-cell"]
    size_display = ["none", "none", "table-cell", "table-cell"]
    index_display = ["none", "none", "none", "table-cell"]
    icon_header_style = {
        **TABLE_HEADER_BASE_STYLE,
        "textAlign": "center",  # ← Fixed: match body cell textAlign: "center"
        "width": "52px",
        "paddingLeft": "8px",
        "paddingRight": "8px",
        "color": "transparent",
        "userSelect": "none",
    }
    action_header_style = {
        **TABLE_HEADER_BASE_STYLE,
        "textAlign": "center",  # ← Fixed: match body cell textAlign: "center"
        "width": "56px",
        "paddingLeft": "8px",
        "paddingRight": "8px",
        "color": "transparent",
        "userSelect": "none",
    }
    return rx.box(
        rx.el.table(
            rx.el.thead(
                rx.el.tr(
                    rx.el.th("", style=icon_header_style),
                    rx.el.th("NAME", style=TABLE_HEADER_BASE_STYLE),
                    rx.el.th("DATE MODIFIED", style=TABLE_HEADER_BASE_STYLE, display=date_display),
                    rx.el.th("TYPE", style=TABLE_HEADER_BASE_STYLE, display=type_display),
                    rx.el.th("SIZE", style=TABLE_HEADER_BASE_STYLE, display=size_display),
                    rx.el.th("STATUS", style=TABLE_HEADER_BASE_STYLE),
                    rx.el.th("INDEX", style=TABLE_HEADER_BASE_STYLE, display=index_display),
                    rx.el.th("", style=action_header_style),
                )
            ),
            rx.el.tbody(
                rx.foreach(
                    FilesState.visible_folder_children,
                    lambda child: active_child_file_row(child),
                )
            ),
            # Fix Bug 3: table-layout fixed makes th widths authoritative for all columns
            style={"width": "100%", "borderCollapse": "collapse", "tableLayout": "fixed"},
            class_name="files-data-table",
        ),
        width="100%",
        margin_top="16px",
        overflow_x=["auto", "auto", "hidden", "hidden"],
        overflow_y="visible",
        border=f"1px solid {_mode('#e5e7eb', '#2d3748')}",
        border_radius="12px",
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
        height="100%",
        min_height="0",
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
            rx.flex(
                rx.hstack(
                    rx.icon("folder-open", size=18, color=accent_muted_fg),
                    rx.text(
                        rx.cond(
                            FilesState.expanded_folder_name != "",
                            FilesState.expanded_folder_name,
                            "Explorer",
                        ),
                        style={
                            "fontSize": ["16px", "18px", "18px", "18px"],
                            "fontWeight": "700",
                            "color": text_primary,
                            "letterSpacing": "-0.02em",
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                            "maxWidth": ["160px", "none", "none", "none"],
                        },
                    ),
                    spacing="2",
                    align="center",
                    flex="1",
                    min_width="0",
                ),
                rx.text(
                    FilesState.active_child_count_label,
                    style={"fontSize": "13px", "color": MUTED_TEXT},
                    display=["none", "block", "block", "block"],
                ),
                rx.spacer(),
                _files_panel_view_toggle(),
                width="100%",
                align="center",
                direction="row",
                gap="8px",
            ),
            rx.text(
                rx.cond(FilesState.expanded_folder_name != "", FilesState.visible_child_count_label, ""),
                style={"fontSize": "13px", "color": MUTED_TEXT},
            ),
            rx.cond(
                FilesState.expanded_folder_name != "",
                rx.text(
                    "Drop files anywhere on this panel to upload to this folder.",
                    style={"fontSize": "13px", "color": MUTED_TEXT},
                ),
            ),
            rx.cond(
                FilesState.expanded_folder_name != "",
                rx.vstack(
                    rx.vstack(
                        # Search input — full width on all breakpoints
                        rx.input(
                            placeholder="Search files...",
                            value=FilesState.search_query,
                            on_change=FilesState.set_search_query,
                            size="2",
                            width="100%",
                            font_size="13px",
                            padding="8px 14px",
                            border_radius="8px",
                            bg=chat_input_bg,
                            border=f"1px solid {_mode('#e5e7eb', '#374151')}",
                            color=text_primary,
                            _placeholder={"color": _mode("#9ca3af", "#6b7280")},
                            _focus={
                                "border_color": chat_input_focus_border,
                                "box_shadow": chat_focus_ring,
                            },
                        ),
                        # Filter chips row — scrollable on all breakpoints
                        rx.box(
                            rx.box(
                                panel_action_button(
                                    "All",
                                    active=FilesState.active_type_filter == "all",
                                    on_click=lambda: FilesState.set_type_filter("all"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.box(
                                panel_action_button(
                                    "PDF",
                                    active=FilesState.active_type_filter == "pdf",
                                    on_click=lambda: FilesState.set_type_filter("pdf"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.box(
                                panel_action_button(
                                    "Image",
                                    active=FilesState.active_type_filter == "image",
                                    on_click=lambda: FilesState.set_type_filter("image"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.box(
                                panel_action_button(
                                    "Doc",
                                    active=FilesState.active_type_filter == "doc",
                                    on_click=lambda: FilesState.set_type_filter("doc"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.box(
                                panel_action_button(
                                    "Sheet",
                                    active=FilesState.active_type_filter == "sheet",
                                    on_click=lambda: FilesState.set_type_filter("sheet"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.box(
                                panel_action_button(
                                    "Uploaded: Newest",
                                    active=(FilesState.sort_mode == "uploaded_desc") | (FilesState.sort_mode == "modified_desc"),
                                    on_click=lambda: FilesState.set_sort_mode("uploaded_desc"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.box(
                                panel_action_button(
                                    "Uploaded: Oldest",
                                    active=(FilesState.sort_mode == "uploaded_asc") | (FilesState.sort_mode == "modified_asc"),
                                    on_click=lambda: FilesState.set_sort_mode("uploaded_asc"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.box(
                                panel_action_button(
                                    "Name A-Z",
                                    active=FilesState.sort_mode == "name_asc",
                                    on_click=lambda: FilesState.set_sort_mode("name_asc"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.box(
                                panel_action_button(
                                    "Size",
                                    active=FilesState.sort_mode == "size_desc",
                                    on_click=lambda: FilesState.set_sort_mode("size_desc"),
                                ),
                                flex_shrink="0",
                            ),
                            rx.cond(
                                FilesState.search_query != "",
                                rx.box(
                                    rx.button(
                                        "Clear",
                                        variant="ghost",
                                        size="1",
                                        on_click=FilesState.clear_search_query,
                                    ),
                                    flex_shrink="0",
                                ),
                            ),
                            display="flex",
                            flex_direction="row",
                            flex_wrap="nowrap",
                            align_items="center",
                            overflow_x="auto",
                            gap="8px",
                            width="100%",
                            padding_bottom="4px",
                            style={"WebkitOverflowScrolling": "touch", "scrollbarWidth": "none", "msOverflowStyle": "none"},
                        ),
                        width="100%",
                        spacing="2",
                        align="start",
                    ),
                    width="100%",
                    spacing="2",
                ),
            ),
            width="100%",
            spacing="1",
            flex_shrink="0",
        ),
        # Scrollable body: empty-state / loading / cards+list / preview
        rx.box(
            # Empty-state when no folder selected (default on load).
            rx.cond(
                FilesState.expanded_folder_name == "",
                files_explorer_no_folder_placeholder(),
            ),
            rx.cond(
                FilesState.is_loading_folder,
                rx.box(
                    rx.vstack(
                        rx.spinner(size="3"),
                        rx.text(
                            rx.cond(
                                FilesState.loading_folder_name != "",
                                f"Loading folder: {FilesState.loading_folder_name}",
                                "Loading folder files...",
                            ),
                            size="2",
                            color=rx.color("gray", 11),
                        ),
                        spacing="2",
                        align="center",
                    ),
                    width="100%",
                    min_height="220px",
                    border=f"1px dashed {BORDER_COLOR}",
                    border_radius="10px",
                    bg=rx.color("gray", 1),
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
            ),
            # Main content area: show either cards/list OR full preview.
            rx.cond(
                FilesState.is_loading_folder == False,
                rx.cond(
                    FilesState.expanded_folder_name != "",
                    rx.cond(
                        FilesState.has_selected_child_file,
                        file_preview_panel(),
                        rx.cond(
                            FilesState.show_no_results_hint,
                            files_no_results_placeholder(),
                            rx.cond(
                                FilesState.show_empty_folder_hint,
                                files_empty_folder_placeholder(),
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
                                            style={
                                                "display": "grid",
                                                "gridTemplateColumns": "repeat(auto-fill, minmax(min(140px, 100%), 1fr))",
                                                "gap": "10px",
                                            },
                                        ),
                                        active_children_table(),
                                    ),
                                    width="100%",
                                    align_self="start",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            flex="1 1 0%",
            overflow_y="auto",
            min_height="0",
            width="100%",
        ),
        spacing="4",
        width="100%",
        height="100%",
        min_height="0",
        align="start",
        display="flex",
        flex_direction="column",
        bg=PANEL_BG,
        border=f"1px solid {_mode('#e5e7eb', '#374151')}",
        border_radius="16px",
        padding=["12px", "16px", "20px", "24px"],
        box_shadow=files_panel_card_shadow,
    )
    return rx.upload.root(
        rx.box(
            inner,
            upload_progress_overlay(compact=False),
            panel_drop_confirm_layer(),
            position="relative",
            width="100%",
            height="100%",
            display="flex",
            flex_direction="column",
        ),
        id=FILES_PANEL_UPLOAD_ZONE_ID,
        width="100%",
        height="100%",
        flex="1",
        display="flex",
        flex_direction="column",
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