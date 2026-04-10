import reflex as rx

from receipt_ai.core.upload_constants import (
    FILES_PANEL_UPLOAD_ZONE_ID,
    FILES_UPLOAD_ZONE_ID,
)
from receipt_ai.features.extraction.models import ExtractionRequest
from receipt_ai.features.extraction.orchestrator import run_upload_extraction
from receipt_ai.features.files.validation import normalize_item_name, validate_upload_filename


class FilesUploadActionsMixin:
    """Upload queue, confirmation, and transfer actions."""

    # Open upload modal from the upload icon button.
    def open_upload_input(self) -> None:
        """Open upload overlay from toolbar upload button."""
        if not self.expanded_folder_name:
            return
        self.show_drop_overlay = True
        self.upload_error = ""
        self.excluded_upload_names = []

    # Cancel active transfer (if any) and close modal.
    def cancel_upload(self) -> list:
        """Cancel active upload and close the overlay."""
        self.show_drop_overlay = False
        self.show_upload_confirm = False
        self.show_panel_drop_confirm = False
        self._pending_panel_drop_files = []
        self.is_uploading = False
        self.upload_error = ""
        self.excluded_upload_names = []
        return [rx.cancel_upload(self.upload_zone_id), rx.clear_selected_files(self.upload_zone_id)]

    def request_upload_confirm(self) -> None:
        """Open confirmation modal before uploading queued files."""
        if self.is_uploading:
            return
        self.upload_error = ""
        self.show_upload_confirm = True

    async def request_panel_drop_confirm(self, files: list[rx.UploadFile]):
        """Open confirmation after a panel drop and stash dropped files."""
        if not self.expanded_folder_name:
            self.upload_error = "Magbukas muna ng folder sa Explorer bago mag-upload."
            return
        if not files:
            return
        self._pending_panel_drop_files = files
        self.upload_error = ""
        self.show_panel_drop_confirm = True

    def cancel_panel_drop_confirm(self):
        """Cancel panel drop upload and clear stashed/selected panel files."""
        self.show_panel_drop_confirm = False
        self._pending_panel_drop_files = []
        return rx.clear_selected_files(FILES_PANEL_UPLOAD_ZONE_ID)

    async def confirm_panel_drop_upload(self):
        """User confirmed: upload stashed files from the panel drop zone."""
        self.show_panel_drop_confirm = False
        files = self._pending_panel_drop_files
        self._pending_panel_drop_files = []
        return await self._upload_to_open_folder(
            files,
            FILES_PANEL_UPLOAD_ZONE_ID,
            use_skip_list=False,
        )

    def cancel_upload_confirm(self) -> None:
        """Close upload confirmation modal."""
        self.show_upload_confirm = False

    def exclude_upload_file(self, filename: str) -> None:
        """Mark selected file to be skipped on upload."""
        if filename not in self.excluded_upload_names:
            self.excluded_upload_names.append(filename)

    def include_upload_file(self, filename: str) -> None:
        """Unskip file and include it again in upload."""
        self.excluded_upload_names = [name for name in self.excluded_upload_names if name != filename]

    def clear_upload_selection(self):
        """Clear staged upload list and skipped markers."""
        self.excluded_upload_names = []
        return rx.clear_selected_files(self.upload_zone_id)

    def track_upload_progress(self, prog: dict) -> None:
        """Drive progress UI during rx.upload_files (Reflex fires ~once per second)."""
        raw = prog.get("progress", prog.get("percentage", prog.get("loaded", 0)))
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = 0.0
        self.upload_progress_pct = max(0, min(100, int(round(val))))

    async def upload_panel_drop(self, files: list[rx.UploadFile]) -> rx.event.EventSpec | None:
        """Direct upload from main panel drop zone (Technical AI right-panel pattern)."""
        return await self._upload_to_open_folder(files, FILES_PANEL_UPLOAD_ZONE_ID, use_skip_list=False)

    async def upload_files(self, files: list[rx.UploadFile]) -> rx.event.EventSpec | None:
        """Upload from modal queue after confirmation (honours excluded_upload_names)."""
        return await self._upload_to_open_folder(files, FILES_UPLOAD_ZONE_ID, use_skip_list=True)

    async def _upload_to_open_folder(
        self,
        files: list[rx.UploadFile],
        clear_zone_id: str,
        *,
        use_skip_list: bool,
    ) -> rx.event.EventSpec | None:
        """Persist uploads to Wasabi for the expanded folder; clear the given upload zone when done."""
        if not files:
            self.upload_error = "No files selected. Add files to the queue or drop them on the panel first."
            return None
        if not self.expanded_folder_name:
            self.upload_error = "Please open a folder first."
            return None

        self.is_uploading = True
        self.upload_error = ""
        self.upload_progress_pct = 0

        try:
            storage = self._get_storage()
            target_folder = self._resolve_storage_folder_name(self.expanded_folder_name)
            uploaded_names: list[str] = []
            existing_names = {child["name"].lower() for child in self.active_folder_children}
            seen_batch: set[str] = set()
            excluded_lower = {name.lower() for name in self.excluded_upload_names} if use_skip_list else set()

            for file in files:
                validation_error = validate_upload_filename(file.filename)
                if validation_error:
                    self.upload_error = validation_error
                    return None
                normalized_name = normalize_item_name(file.filename)
                lowered = normalized_name.lower()
                if lowered in excluded_lower:
                    continue
                if lowered in existing_names:
                    self.upload_error = f"File '{normalized_name}' already exists in this folder."
                    return None
                if lowered in seen_batch:
                    self.upload_error = f"Duplicate file in selection: '{normalized_name}'."
                    return None
                seen_batch.add(lowered)

                await file.seek(0)
                file_bytes = await file.read()
                await file.seek(0)
                storage.upload_fileobj(target_folder, file.filename, file.file)
                uploaded_names.append(file.filename)

                extraction_result = await run_upload_extraction(
                    ExtractionRequest(
                        filename=file.filename,
                        content_type=getattr(file, "content_type", None),
                        file_bytes=file_bytes,
                        storage_folder=target_folder,
                    )
                )
                if extraction_result.status == "failed":
                    # Upload remains successful; extraction errors are surfaced as non-blocking notice.
                    self.upload_error = f"Upload succeeded but extraction failed for '{file.filename}': {extraction_result.error}"

            self._reload_folder_children(target_folder)
            if uploaded_names:
                self.select_child_file(uploaded_names[-1])
            else:
                self.upload_error = "No files selected for upload."
                return None

            self.excluded_upload_names = []
            self.show_upload_confirm = False
            self.show_panel_drop_confirm = False
            self.show_drop_overlay = False
            return rx.clear_selected_files(clear_zone_id)
        except Exception as e:
            self.upload_error = f"Upload failed: {e}"
            return None
        finally:
            self.is_uploading = False
            self.upload_progress_pct = 0
