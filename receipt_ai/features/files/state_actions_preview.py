import csv
import io
from urllib.parse import quote

import reflex as rx


class FilesPreviewActionsMixin:
    """Preview and download actions for selected file."""

    def _refresh_preview_url(self) -> None:
        """Build preview data for selected file (url/text/embed) in the same panel."""
        self._clear_preview_state()
        if not self.expanded_folder_name or not self.selected_child_file_name:
            return
        try:
            storage = self._get_storage()
            storage_folder = self._resolve_storage_folder_name(self.expanded_folder_name)
            rel = f"{storage_folder}/{self.selected_child_file_name}"
            self.preview_url = storage.presigned_get_url(rel)
            ext = self.selected_child_file_name.rsplit(".", 1)[-1].lower() if "." in self.selected_child_file_name else ""

            # Text-like files: read content directly for inline preview.
            if ext in {"txt", "md", "csv"}:
                self.preview_text = storage.read_text(rel)
            if ext == "csv":
                parsed_rows = list(csv.reader(io.StringIO(self.preview_text)))
                if parsed_rows:
                    headers = parsed_rows[0]
                    if not headers:
                        headers = [f"Column {idx + 1}" for idx in range(max((len(r) for r in parsed_rows), default=1))]
                    # Show a sample window for performance.
                    body_rows = parsed_rows[1:121]
                    col_count = len(headers)
                    normalized_rows: list[list[str]] = []
                    for row in body_rows:
                        if len(row) < col_count:
                            normalized_rows.append(row + [""] * (col_count - len(row)))
                        else:
                            normalized_rows.append(row[:col_count])
                    self.preview_csv_headers = headers
                    self.preview_csv_rows = normalized_rows

            # Office files: preview via Office online viewer.
            if ext in {"doc", "docx", "xls", "xlsx"}:
                encoded = quote(self.preview_url, safe="")
                self.preview_embed_url = f"https://view.officeapps.live.com/op/embed.aspx?src={encoded}"
        except Exception as e:
            self.preview_error = f"Failed to load preview: {e}"

    # Select a file in the expanded folder (sidebar or main panel) and load preview.
    def select_child_file(self, filename: str) -> None:
        """Mark a child file as selected and refresh the inline preview URL."""
        self.selected_child_file_name = filename
        self._refresh_preview_url()

    def close_preview(self) -> None:
        """Close inline preview and return to the cards/list view."""
        self.selected_child_file_name = ""
        self._clear_preview_state()

    def download_selected_file(self):
        """Download the currently selected file using a presigned URL."""
        if not self.expanded_folder_name or not self.selected_child_file_name:
            self.upload_error = "Select a file to download."
            return
        try:
            storage = self._get_storage()
            storage_folder = self._resolve_storage_folder_name(self.expanded_folder_name)
            rel = f"{storage_folder}/{self.selected_child_file_name}"
            url = storage.presigned_get_url(rel, inline=False)
            return rx.redirect(url, is_external=True)
        except Exception as e:
            self.upload_error = f"Failed to download file: {e}"
