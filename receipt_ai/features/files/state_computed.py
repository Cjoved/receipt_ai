import reflex as rx
from typing import Any

from receipt_ai.features.files.file_meta import child_file_meta
from receipt_ai.features.files.validation import (
    duplicate_name_error,
    normalize_item_name,
    validate_item_name,
)


class FilesComputedMixin:
    """Computed vars for FilesState, split for maintainability."""

    @rx.var
    def upload_progress_label(self) -> str:
        """Whole percent for upload overlay (Technical AI progress card)."""
        return f"{self.upload_progress_pct}%"

    @rx.var
    def sidebar_width_css(self) -> str:
        """Left explorer width as a CSS percentage (desktop split)."""
        return f"{self.sidebar_width_pct}%"

    @rx.var
    def main_panel_width_css(self) -> str:
        """Right column width as a CSS percentage (desktop split)."""
        return f"{100 - self.sidebar_width_pct}%"

    @rx.var
    # True when a folder expanded (enables folder-only actions)
    def has_open_folder(self) -> bool:
        return self.expanded_folder_name != ""

    @rx.var
    def has_selected_child_file(self) -> bool:
        """True when a file inside the expanded folder is selected (for view / file delete)."""
        return self.selected_child_file_name != ""

    @rx.var
    def new_folder_validation_error(self) -> str:
        """Frontend validation message for create-folder input."""
        if not self.show_new_folder_input:
            return ""
        candidate = normalize_item_name(self.new_folder_name)
        if candidate == "":
            return ""
        base_error = validate_item_name(candidate, kind="folder")
        if base_error:
            return base_error
        duplicate_error = duplicate_name_error(candidate, set(self.folder_names), kind="folder")
        return duplicate_error or ""

    @rx.var
    def can_create_new_folder(self) -> bool:
        """Enable Create button only for valid folder names."""
        candidate = normalize_item_name(self.new_folder_name)
        return candidate != "" and self.new_folder_validation_error == ""

    @rx.var
    def rename_validation_error(self) -> str:
        """Frontend validation message for rename input."""
        if not self.show_rename_input:
            return ""
        candidate = normalize_item_name(self.rename_value)
        if candidate == "":
            return ""
        kind = "file" if self.selected_child_file_name else "folder"
        base_error = validate_item_name(candidate, kind=kind)
        if base_error:
            return base_error
        if self.selected_child_file_name:
            existing = {
                child["name"]
                for child in self.active_folder_children
                if child.get("name", "").lower() != self.selected_child_file_name.lower()
            }
            duplicate_error = duplicate_name_error(candidate, existing, kind="file")
            return duplicate_error or ""
        if self.expanded_folder_name:
            existing_folders = {name for name in self.folder_names if name.lower() != self.expanded_folder_name.lower()}
            duplicate_error = duplicate_name_error(candidate, existing_folders, kind="folder")
            return duplicate_error or ""
        return ""

    @rx.var
    def can_save_rename(self) -> bool:
        """Enable Save only when rename input is valid."""
        candidate = normalize_item_name(self.rename_value)
        return candidate != "" and self.rename_validation_error == ""

    @rx.var
    def delete_target_label(self) -> str:
        """Readable name for delete confirmation body."""
        if self.selected_child_file_name:
            return self.selected_child_file_name
        return self.expanded_folder_name

    @rx.var
    def active_child_count_label(self) -> str:
        """Formatted item count label for the files panel header."""
        count = len(self.active_folder_children)
        return f"{count} item(s)"

    @rx.var
    def visible_child_count_label(self) -> str:
        """Count label for currently visible (filtered/searched) files."""
        count = len(self.visible_folder_children)
        return f"{count} visible"

    @rx.var
    def stats_total_files(self) -> str:
        """Total files count in opened folder (before filters)."""
        return str(len(self.active_folder_children))

    @rx.var
    def stats_total_size_label(self) -> str:
        """Total storage consumed by files in opened folder."""
        total = sum(int(row.get("size_bytes", "0")) for row in self.active_folder_children)
        return self._format_size(total)

    @rx.var
    def stats_pdf_count(self) -> str:
        """Number of PDF files in opened folder."""
        count = sum(1 for row in self.active_folder_children if row.get("type") == "PDF")
        return str(count)

    @rx.var
    def stats_image_count(self) -> str:
        """Number of image files in opened folder."""
        count = sum(1 for row in self.active_folder_children if row.get("type") == "Image")
        return str(count)

    @rx.var
    def stats_latest_modified_label(self) -> str:
        """Most recent modified timestamp in opened folder."""
        if not self.active_folder_children:
            return "-"
        latest = max(
            self.active_folder_children,
            key=lambda row: int(row.get("modified_epoch", "0")),
        )
        return latest.get("modified_at", "-")

    @rx.var
    def preview_display_kind(self) -> str:
        """How to render inline preview: none | image | pdf | csv | text | office | other."""
        name = (self.selected_child_file_name or "").lower()
        if not name:
            return "none"
        if "." not in name:
            return "other"
        ext = name.rsplit(".", 1)[-1]
        if ext in {"png", "jpg", "jpeg", "gif", "webp", "svg"}:
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

    @rx.var
    # Folder-only list for rendering expandable rows in sidebar.
    def folder_names(self) -> list[str]:
        return [item["name"] for item in self.files if item.get("file_type", "").lower() == "folder"]

    @rx.var
    # Child file rows for the currently expanded folder.
    def active_folder_children(self) -> list[dict[str, str]]:
        if not self.expanded_folder_name:
            return []
        children: list[Any] = self.folder_children.get(self.expanded_folder_name, [])
        normalized: list[dict[str, str]] = []
        for child in children:
            if isinstance(child, dict):
                name = child.get("name", "")
                if name:
                    normalized.append(
                        {
                            "name": name,
                            "ext": child.get("ext", "FILE"),
                            "icon": child.get("icon", "file"),
                            "badge": child.get("badge", "gray"),
                            "type": child.get("type", "File"),
                            "size": child.get("size", "-"),
                            "size_bytes": child.get("size_bytes", "0"),
                            "modified_at": child.get("modified_at", "-"),
                            "modified_epoch": child.get("modified_epoch", "0"),
                            "status": child.get("status", "Completed"),
                        }
                    )
            elif isinstance(child, str):
                normalized.append(self._hydrate_child(child))
        return normalized

    @rx.var
    def visible_folder_children(self) -> list[dict[str, str]]:
        """Filtered and sorted children for table/grid rendering."""
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
