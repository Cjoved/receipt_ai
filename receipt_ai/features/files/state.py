import reflex as rx
from datetime import datetime
from typing import Any

from receipt_ai.core.upload_constants import FILES_UPLOAD_ZONE_ID
from receipt_ai.features.files.file_meta import child_file_meta
from receipt_ai.features.files.service import list_files_payload
from receipt_ai.features.files.state_actions_crud import FilesCrudActionsMixin
from receipt_ai.features.files.state_actions_preview import FilesPreviewActionsMixin
from receipt_ai.features.files.state_actions_upload import FilesUploadActionsMixin
from receipt_ai.features.files.state_computed import FilesComputedMixin
from receipt_ai.features.storage.wasabi import WasabiConfig, WasabiStorage


# Module-level singleton cache (not part of Reflex state serialization).
_WASABI_STORAGE: WasabiStorage | None = None

# Explorer split: client drag until mouseup; Promise resolves width % (rx.call_script + callback).
_EXPLORER_DIVIDER_DRAG_JS = """
return new Promise((resolve) => {
  const root = document.getElementById("files-split-root");
  if (!root) {
    resolve(28);
    return;
  }
  const prevSelect = document.body.style.userSelect;
  document.body.style.userSelect = "none";
  const move = (e) => {
    const r = root.getBoundingClientRect();
    if (r.width <= 0) return;
    let p = ((e.clientX - r.left) / r.width) * 100;
    p = Math.max(20, Math.min(80, p));
    root.style.setProperty("--files-sidebar-pct", p + "%");
  };
  const up = () => {
    window.removeEventListener("mousemove", move);
    document.body.style.userSelect = prevSelect;
    const raw = getComputedStyle(root).getPropertyValue("--files-sidebar-pct").trim() || "28%";
    const n = parseFloat(raw);
    resolve(Number.isFinite(n) ? Math.round(n) : 28);
  };
  window.addEventListener("mousemove", move);
  window.addEventListener("mouseup", up, { once: true });
});
"""


def get_storage() -> WasabiStorage:
    """Get or create shared Wasabi storage adapter."""
    global _WASABI_STORAGE
    if _WASABI_STORAGE is None:
        _WASABI_STORAGE = WasabiStorage(WasabiConfig.from_env())
    return _WASABI_STORAGE


class FilesState(
    FilesComputedMixin,
    FilesCrudActionsMixin,
    FilesPreviewActionsMixin,
    FilesUploadActionsMixin,
    rx.State,
):
    """State container for files feature."""

    # Files page layout: resizable sidebar (desktop) + mobile tree/content switch.
    sidebar_width_pct: int = 28
    files_mobile_view: str = "tree"

    files: list[dict[str, str]] = list_files_payload()
    selected_file_name: str = files[0]["name"] if files else ""
    show_new_folder_input: bool = False
    new_folder_name: str = ""
    show_rename_input: bool = False
    rename_value: str = ""
    view_mode: str = "list"
    show_delete_confirm: bool = False
    show_rename_confirm: bool = False
    show_upload_confirm: bool = False
    search_query: str = ""
    active_type_filter: str = "all"
    sort_mode: str = "modified_desc"

    # Upload overlay state (global drag/drop modal).
    show_drop_overlay: bool = False
    is_uploading: bool = False
    upload_progress_pct: int = 0
    upload_error: str = ""
    upload_zone_id: str = FILES_UPLOAD_ZONE_ID
    excluded_upload_names: list[str] = []

    # Which folder is currently expanded in the sidebar.
    expanded_folder_name: str = ""
    # Selected file inside the expanded folder (empty = toolbar targets the folder).
    selected_child_file_name: str = ""
    # Presigned URL for inline preview in the main panel (no navigation away).
    preview_url: str = ""
    # Office iframe URL for doc/docx/xls/xlsx preview.
    preview_embed_url: str = ""
    # Raw text content for txt/csv/md preview.
    preview_text: str = ""
    # Structured CSV preview content (header + sample rows).
    preview_csv_headers: list[str] = []
    preview_csv_rows: list[list[str]] = []
    preview_error: str = ""

    # Demo children files per folder (local mock for now).
    folder_children: dict[str, list[dict[str, str]]] = {
        "My Files": [
            {"name": "invoice_jan.pdf", "ext": "PDF", "icon": "file-text", "badge": "red"},
            {"name": "receipt_store.png", "ext": "PNG", "icon": "file-image", "badge": "purple"},
            {"name": "report.xlsx", "ext": "XLSX", "icon": "file-spreadsheet", "badge": "green"},
        ],
    }

    @rx.var
    def has_open_folder(self) -> bool:
        return self.expanded_folder_name != ""

    @rx.var
    def has_selected_child_file(self) -> bool:
        return self.selected_child_file_name != ""

    @rx.var
    def active_folder_children(self) -> list[dict[str, str]]:
        if not self.expanded_folder_name:
            return []
        children = self.folder_children.get(self.expanded_folder_name, [])
        normalized: list[dict[str, str]] = []
        for child in children:
            if not isinstance(child, dict):
                continue
            name = str(child.get("name", "")).strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "ext": str(child.get("ext", "FILE")),
                    "icon": str(child.get("icon", "file")),
                    "badge": str(child.get("badge", "gray")),
                    "type": str(child.get("type", "File")),
                    "size": str(child.get("size", "-")),
                    "size_bytes": str(child.get("size_bytes", "0")),
                    "modified_at": str(child.get("modified_at", "-")),
                    "modified_epoch": str(child.get("modified_epoch", "0")),
                    "status": str(child.get("status", "Completed")),
                }
            )
        return normalized

    @rx.var
    def visible_folder_children(self) -> list[dict[str, str]]:
        rows = list(self.active_folder_children)
        query = self.search_query.strip().lower()
        filter_key = self.active_type_filter.lower()

        if query:
            rows = [row for row in rows if query in row.get("name", "").lower()]

        if filter_key != "all":
            filter_map: dict[str, set[str]] = {
                "pdf": {"PDF"},
                "image": {"Image"},
                "doc": {"Document"},
                "sheet": {"Spreadsheet"},
                "archive": {"Archive"},
                "other": {"File"},
            }
            allowed = filter_map.get(filter_key, set())
            rows = [row for row in rows if row.get("type", "") in allowed]

        if self.sort_mode == "name_asc":
            rows.sort(key=lambda row: row.get("name", "").lower())
        elif self.sort_mode == "name_desc":
            rows.sort(key=lambda row: row.get("name", "").lower(), reverse=True)
        elif self.sort_mode == "size_desc":
            rows.sort(key=lambda row: int(row.get("size_bytes", "0")), reverse=True)
        elif self.sort_mode == "size_asc":
            rows.sort(key=lambda row: int(row.get("size_bytes", "0")))
        elif self.sort_mode == "modified_asc":
            rows.sort(key=lambda row: int(row.get("modified_epoch", "0")))
        else:
            rows.sort(key=lambda row: int(row.get("modified_epoch", "0")), reverse=True)
        return rows

    @rx.var
    def visible_child_count_label(self) -> str:
        return f"{len(self.visible_folder_children)} visible"

    @rx.var
    def stats_total_files(self) -> str:
        return str(len(self.active_folder_children))

    @rx.var
    def stats_total_size_label(self) -> str:
        total = sum(int(row.get("size_bytes", "0")) for row in self.active_folder_children)
        return self._format_size(total)

    @rx.var
    def stats_pdf_count(self) -> str:
        return str(sum(1 for row in self.active_folder_children if row.get("type") == "PDF"))

    @rx.var
    def stats_image_count(self) -> str:
        return str(sum(1 for row in self.active_folder_children if row.get("type") == "Image"))

    @rx.var
    def stats_latest_modified_label(self) -> str:
        if not self.active_folder_children:
            return "-"
        latest = max(self.active_folder_children, key=lambda row: int(row.get("modified_epoch", "0")))
        return latest.get("modified_at", "-")

    @rx.var
    def preview_display_kind(self) -> str:
        """Resolve preview renderer kind from selected file metadata and extension."""
        name = (self.selected_child_file_name or "").strip()
        if not name:
            return "none"

        # Prefer hydrated metadata when available (more reliable than extension parsing alone).
        selected_row = next(
            (row for row in self.active_folder_children if row.get("name", "") == name),
            None,
        )
        selected_type = str(selected_row.get("type", "")).lower() if selected_row else ""
        if selected_type == "image":
            return "image"
        if selected_type == "pdf":
            return "pdf"
        if selected_type == "spreadsheet":
            return "csv" if name.lower().endswith(".csv") else "office"
        if selected_type == "document":
            return "text" if name.lower().endswith((".txt", ".md")) else "office"

        # Fallback to extension-based detection.
        lowered = name.lower().split("?", 1)[0].split("#", 1)[0].strip()
        if "." not in lowered:
            return "other"
        ext = lowered.rsplit(".", 1)[-1].strip(" )].,;")
        if ext in {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "jfif"}:
            return "image"
        if ext == "pdf":
            return "pdf"
        if ext == "csv":
            return "csv"
        if ext in {"txt", "md"}:
            return "text"
        if ext in {"doc", "docx", "xls", "xlsx"}:
            return "office"
        return "other"

    # --- Shared helpers used by action/computed mixins ---
    def _format_size(self, size_bytes: int) -> str:
        """Human-readable size label for table/card display."""
        if size_bytes <= 0:
            return "-"
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size_bytes)
        idx = 0
        while value >= 1024 and idx < len(units) - 1:
            value /= 1024
            idx += 1
        return f"{value:.1f} {units[idx]}"

    def _format_modified(self, value: Any) -> str:
        """Format LastModified datetime into compact label."""
        if isinstance(value, datetime):
            return value.strftime("%b %d, %Y %I:%M %p")
        return "-"

    def _modified_epoch(self, value: Any) -> int:
        """Sortable epoch value for LastModified."""
        if isinstance(value, datetime):
            return int(value.timestamp())
        return 0

    def _hydrate_child(self, name: str, size_bytes: int = 0, modified_at: Any = None) -> dict[str, str]:
        """Attach table/grid metadata on top of extension icon metadata."""
        meta = child_file_meta(name)
        return {
            **meta,
            "size": self._format_size(size_bytes),
            "size_bytes": str(size_bytes),
            "modified_at": self._format_modified(modified_at),
            "modified_epoch": str(self._modified_epoch(modified_at)),
            "status": "Completed",
        }

    def _reload_folder_children(self, folder_name: str) -> None:
        """Refresh folder files from Wasabi with full metadata."""
        storage = self._get_storage()
        storage_folder = self._resolve_storage_folder_name(folder_name)
        file_objects = storage.list_folder_file_objects(storage_folder)
        hydrated_children = [
            self._hydrate_child(
                str(obj.get("name", "")),
                int(obj.get("size_bytes", 0) or 0),
                obj.get("last_modified"),
            )
            for obj in file_objects
            if obj.get("name")
        ]
        # Reassign dictionary so Reflex reliably detects state change.
        self.folder_children = {**self.folder_children, folder_name: hydrated_children}

    def _clear_preview_state(self) -> None:
        """Reset all preview buffers and URLs in one place."""
        self.preview_url = ""
        self.preview_embed_url = ""
        self.preview_text = ""
        self.preview_csv_headers = []
        self.preview_csv_rows = []
        self.preview_error = ""

    # Access shared Wasabi adapter outside serialized Reflex state.
    def _get_storage(self) -> WasabiStorage:
        return get_storage()

    def set_sidebar_width_pct(self, value: int) -> None:
        """Clamp to TA Dashboard range (20%–80%)."""
        self.sidebar_width_pct = max(20, min(80, int(value)))

    def commit_sidebar_width_from_drag(self, value: Any) -> None:
        """Apply width % returned from client after explorer divider drag ends."""
        try:
            n = int(round(float(value)))
        except (TypeError, ValueError):
            n = int(self.sidebar_width_pct)
        self.set_sidebar_width_pct(n)

    def on_explorer_divider_mouse_down(self):
        """Start client-side drag; syncs state once on mouseup."""
        return rx.call_script(
            _EXPLORER_DIVIDER_DRAG_JS,
            callback=FilesState.commit_sidebar_width_from_drag,
        )

    def set_files_mobile_view(self, view: str) -> None:
        if view in ("tree", "content"):
            self.files_mobile_view = view

    def show_files_tree_mobile(self) -> None:
        self.files_mobile_view = "tree"

    def show_files_content_mobile(self) -> None:
        self.files_mobile_view = "content"

    def _resolve_storage_folder_name(self, folder_name: str) -> str:
        """Map UI folder label to actual Wasabi folder key when names differ."""
        if not folder_name:
            return folder_name
        storage = self._get_storage()
        try:
            folders = storage.list_folders()
        except Exception:
            return folder_name
        if folder_name in folders:
            return folder_name

        candidates = [
            folder_name.replace(" ", "_"),
            folder_name.replace("_", " "),
        ]
        for candidate in candidates:
            if candidate in folders:
                return candidate

        # Last fallback: compare normalized names (ignore spaces/underscores and case).
        normalized_target = folder_name.replace(" ", "").replace("_", "").lower()
        for existing in folders:
            if existing.replace(" ", "").replace("_", "").lower() == normalized_target:
                return existing
        return folder_name

    # --- Event handlers defined on FilesState (safe for Reflex binding) ---
    def load_files(self) -> None:
        return FilesCrudActionsMixin.load_files(self)

    def open_new_folder_input(self) -> None:
        return FilesCrudActionsMixin.open_new_folder_input(self)

    def cancel_new_folder(self) -> None:
        return FilesCrudActionsMixin.cancel_new_folder(self)

    def set_new_folder_name(self, value: str) -> None:
        return FilesCrudActionsMixin.set_new_folder_name(self, value)

    def create_new_folder(self) -> None:
        return FilesCrudActionsMixin.create_new_folder(self)

    def open_rename_input(self) -> None:
        return FilesCrudActionsMixin.open_rename_input(self)

    def set_rename_value(self, value: str) -> None:
        return FilesCrudActionsMixin.set_rename_value(self, value)

    def save_rename(self) -> None:
        return FilesCrudActionsMixin.save_rename(self)

    def cancel_rename(self) -> None:
        return FilesCrudActionsMixin.cancel_rename(self)

    def request_rename_confirm(self) -> None:
        return FilesCrudActionsMixin.request_rename_confirm(self)

    def cancel_rename_confirm(self) -> None:
        return FilesCrudActionsMixin.cancel_rename_confirm(self)

    def delete_file(self) -> None:
        return FilesCrudActionsMixin.delete_file(self)

    def request_delete_confirm(self) -> None:
        return FilesCrudActionsMixin.request_delete_confirm(self)

    def request_delete_child_confirm(self, filename: str) -> None:
        return FilesCrudActionsMixin.request_delete_child_confirm(self, filename)

    def cancel_delete_confirm(self) -> None:
        return FilesCrudActionsMixin.cancel_delete_confirm(self)

    def confirm_delete(self) -> None:
        return FilesCrudActionsMixin.confirm_delete(self)

    def delete_child_file(self, filename: str) -> None:
        return FilesCrudActionsMixin.delete_child_file(self, filename)

    def toggle_folder(self, folder_name: str) -> None:
        return FilesCrudActionsMixin.toggle_folder(self, folder_name)

    def set_grid_view(self) -> None:
        return FilesCrudActionsMixin.set_grid_view(self)

    def set_list_view(self) -> None:
        return FilesCrudActionsMixin.set_list_view(self)

    def set_search_query(self, value: str) -> None:
        return FilesCrudActionsMixin.set_search_query(self, value)

    def clear_search_query(self) -> None:
        return FilesCrudActionsMixin.clear_search_query(self)

    def set_type_filter(self, value: str) -> None:
        return FilesCrudActionsMixin.set_type_filter(self, value)

    def set_sort_mode(self, value: str) -> None:
        return FilesCrudActionsMixin.set_sort_mode(self, value)

    def _refresh_preview_url(self) -> None:
        return FilesPreviewActionsMixin._refresh_preview_url(self)

    def select_child_file(self, filename: str) -> None:
        return FilesPreviewActionsMixin.select_child_file(self, filename)

    def close_preview(self) -> None:
        return FilesPreviewActionsMixin.close_preview(self)

    def download_selected_file(self):
        return FilesPreviewActionsMixin.download_selected_file(self)

    def open_upload_input(self) -> None:
        return FilesUploadActionsMixin.open_upload_input(self)

    def cancel_upload(self) -> list:
        return FilesUploadActionsMixin.cancel_upload(self)

    def request_upload_confirm(self) -> None:
        return FilesUploadActionsMixin.request_upload_confirm(self)

    def cancel_upload_confirm(self) -> None:
        return FilesUploadActionsMixin.cancel_upload_confirm(self)

    def exclude_upload_file(self, filename: str) -> None:
        return FilesUploadActionsMixin.exclude_upload_file(self, filename)

    def include_upload_file(self, filename: str) -> None:
        return FilesUploadActionsMixin.include_upload_file(self, filename)

    def clear_upload_selection(self):
        return FilesUploadActionsMixin.clear_upload_selection(self)

    async def upload_files(self, files: list[rx.UploadFile]):
        return await FilesUploadActionsMixin.upload_files(self, files)

    async def upload_panel_drop(self, files: list[rx.UploadFile]):
        return await FilesUploadActionsMixin.upload_panel_drop(self, files)

    def track_upload_progress(self, prog: dict):
        return FilesUploadActionsMixin.track_upload_progress(self, prog)
