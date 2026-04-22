import reflex as rx
import base64
import fitz

from receipt_ai.core.upload_constants import (
    FILES_PANEL_UPLOAD_ZONE_ID,
    FILES_UPLOAD_ZONE_ID,
)
from receipt_ai.features.extraction.indexing import IndexingRequest
from receipt_ai.features.extraction.jobs import enqueue_uploaded_document
from receipt_ai.features.extraction.models import ExtractionRequest
from receipt_ai.features.extraction.orchestrator import run_upload_extraction
from receipt_ai.features.files.validation import normalize_item_name, validate_upload_filename

# Process-local stash for UploadFile objects (cannot live in serialized Reflex state).
# Keys are per browser session + route so a follow-up handler tick can still read files
# after `confirm_upload_from_queue` chains to `run_confirmed_queue_upload`.
_MODAL_UPLOAD_FILES_BY_KEY: dict[str, list[rx.UploadFile]] = {}
_PANEL_UPLOAD_FILES_BY_KEY: dict[str, list[rx.UploadFile]] = {}


class FilesUploadActionsMixin:
    """Upload queue, confirmation, and transfer actions."""

    def _upload_stash_key(self) -> str:
        """Stable key for the current websocket/browser session (not serialized in state)."""
        router = getattr(self, "router_data", None)
        session = getattr(router, "session", None) if router is not None else None
        token = str(getattr(session, "client_token", "") or "").strip()
        sid = str(getattr(session, "session_id", "") or "").strip()
        route = str(getattr(router, "route_id", "") or "").strip() if router is not None else ""
        base = token or sid
        if base:
            return f"{base}:{route}" if route else base
        # Extremely defensive fallback (should not happen in a real browser event).
        return f"state:{id(self)}"

    def _reset_upload_loading_state(self) -> None:
        """Force-hide upload loading UI and clear progress state."""
        self.is_uploading = False
        self.upload_stage = ""
        self.upload_stage_detail = ""
        self.upload_total_files = 0
        self.upload_completed_files = 0
        self.upload_progress_pct = 0

    def _set_upload_pipeline_progress(self, file_idx: int, phase: str) -> None:
        """Map per-file pipeline phases to a smoother total percent."""
        total = max(1, int(self.upload_total_files))
        index = min(max(1, int(file_idx)), total)
        base = (index - 1) / total
        phase_fraction = {
            "uploading": 0.42,
            "extracting": 0.74,
            "indexing": 0.90,
            "done": 1.00,
        }.get(phase, 0.0)
        weighted = int(round((base + (phase_fraction / total)) * 95))
        self.upload_progress_pct = max(self.upload_progress_pct, min(95, weighted))

    def _stash_set_modal_files(self, files: list[rx.UploadFile]) -> None:
        """Store modal UploadFile objects outside declared state (not serialized)."""
        _MODAL_UPLOAD_FILES_BY_KEY[self._upload_stash_key()] = list(files)

    def _stash_clear_modal_files(self) -> None:
        _MODAL_UPLOAD_FILES_BY_KEY.pop(self._upload_stash_key(), None)

    def _stash_set_panel_files(self, files: list[rx.UploadFile]) -> None:
        _PANEL_UPLOAD_FILES_BY_KEY[self._upload_stash_key()] = list(files)

    def _stash_clear_panel_files(self) -> None:
        _PANEL_UPLOAD_FILES_BY_KEY.pop(self._upload_stash_key(), None)

    # Open upload modal from the upload icon button.
    def open_upload_input(self) -> None:
        """Open upload overlay from toolbar upload button."""
        if not self.expanded_folder_name:
            return
        self.show_drop_overlay = True
        self.show_queued_preview = False
        self.queued_preview_name = ""
        self.queued_preview_url = ""
        self.queued_preview_kind = ""
        self.queued_preview_pages = []
        self.upload_queue_previews = []
        self.upload_queue_pdf_pages = {}
        self.upload_error = ""
        self.excluded_upload_names = []
        self._stash_clear_modal_files()

    # Cancel active transfer (if any) and close modal.
    def cancel_upload(self) -> list:
        """Cancel active upload and close the overlay."""
        self.show_drop_overlay = False
        self.show_upload_confirm = False
        self.show_panel_drop_confirm = False
        self._stash_clear_panel_files()
        self.is_uploading = False
        self.show_queued_preview = False
        self.queued_preview_name = ""
        self.queued_preview_url = ""
        self.queued_preview_kind = ""
        self.queued_preview_pages = []
        self.upload_queue_previews = []
        self.upload_queue_pdf_pages = {}
        self.upload_stage = ""
        self.upload_stage_detail = ""
        self.upload_total_files = 0
        self.upload_completed_files = 0
        self.upload_progress_pct = 0
        self.upload_error = ""
        self.excluded_upload_names = []
        self._stash_clear_modal_files()
        return [rx.cancel_upload(self.upload_zone_id), rx.clear_selected_files(self.upload_zone_id)]

    def request_upload_confirm(self) -> None:
        """Open confirmation modal before uploading queued files."""
        if self.is_uploading:
            return
        if not self.expanded_folder_name:
            self.upload_error = "Please open a folder first."
            self.show_upload_confirm = False
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
        self._stash_set_panel_files(files)
        self.upload_error = ""
        self.show_panel_drop_confirm = True

    def cancel_panel_drop_confirm(self):
        """Cancel panel drop upload and clear stashed/selected panel files."""
        self.show_panel_drop_confirm = False
        self._stash_clear_panel_files()
        return rx.clear_selected_files(FILES_PANEL_UPLOAD_ZONE_ID)

    async def confirm_panel_drop_upload(self):
        """User confirmed: upload stashed files from the panel drop zone."""
        self.show_panel_drop_confirm = False
        files = list(_PANEL_UPLOAD_FILES_BY_KEY.get(self._upload_stash_key(), []))
        self._stash_clear_panel_files()
        return await self._upload_to_open_folder(
            files,
            FILES_PANEL_UPLOAD_ZONE_ID,
            use_skip_list=False,
        )

    def cancel_upload_confirm(self) -> None:
        """Close upload confirmation modal."""
        self.show_upload_confirm = False

    def confirm_upload_from_queue(self):
        """Confirm upload in two steps so loading UI renders before heavy async work."""
        if self.is_uploading:
            return
        self.show_upload_confirm = False
        self.show_panel_drop_confirm = False
        # Step 1: push loading state to UI immediately.
        self.is_uploading = True
        self.upload_error = ""
        self.upload_progress_pct = 0
        self.upload_stage = "preparing"
        self.upload_stage_detail = "Validating receipt files..."
        self.upload_completed_files = 0
        self.upload_total_files = 0
        # Step 2: continue upload in next event tick.
        return type(self).run_confirmed_queue_upload

    async def run_confirmed_queue_upload(self):
        """Execute modal upload with streamed UI updates (progress + stage text)."""
        files = list(_MODAL_UPLOAD_FILES_BY_KEY.get(self._upload_stash_key(), []))
        if not self.expanded_folder_name:
            self.upload_error = "Please open a folder first."
            self.show_upload_confirm = False
            self.show_panel_drop_confirm = False
            self.show_drop_overlay = False
            self._reset_upload_loading_state()
            yield rx.toast.warning(self.upload_error)
            return
        if not files:
            self.upload_error = "No files selected. Add files to the queue or drop them on the panel first."
            self.show_upload_confirm = False
            self._reset_upload_loading_state()
            yield rx.toast.warning(self.upload_error)
            return

        excluded_lower = {name.lower() for name in self.excluded_upload_names}
        queued_files = [file for file in files if normalize_item_name(file.filename).lower() not in excluded_lower]
        if not queued_files:
            self.upload_error = "Walang ia-upload: pumili ng file o i-undo ang Removed."
            self.show_upload_confirm = False
            self._reset_upload_loading_state()
            yield rx.toast.warning(self.upload_error)
            return

        self.upload_total_files = len(queued_files)
        self.upload_progress_pct = 3
        yield

        try:
            storage = self._get_storage()
            target_folder = self._resolve_storage_folder_name(self.expanded_folder_name)
            uploaded_names: list[str] = []
            existing_names = {child["name"].lower() for child in self.active_folder_children}
            seen_batch: set[str] = set()

            for file_idx, file in enumerate(queued_files, start=1):
                validation_error = validate_upload_filename(file.filename)
                if validation_error:
                    self.upload_error = validation_error
                    yield rx.toast.warning(self.upload_error)
                    return

                normalized_name = normalize_item_name(file.filename)
                lowered = normalized_name.lower()
                if lowered in existing_names:
                    self.upload_error = f"File '{normalized_name}' already exists in this folder."
                    yield rx.toast.warning(self.upload_error)
                    return
                if lowered in seen_batch:
                    self.upload_error = f"Duplicate file in selection: '{normalized_name}'."
                    yield rx.toast.warning(self.upload_error)
                    return
                seen_batch.add(lowered)

                self.upload_stage = "uploading"
                self.upload_stage_detail = f"Uploading receipt {normalized_name} ({file_idx}/{self.upload_total_files})..."
                self._set_upload_pipeline_progress(file_idx, "uploading")
                yield

                await file.seek(0)
                file_bytes = await file.read()
                await file.seek(0)
                storage.upload_fileobj(target_folder, file.filename, file.file)
                uploaded_names.append(file.filename)
                self.upload_completed_files = len(uploaded_names)
                yield

                self.upload_stage = "extracting"
                self.upload_stage_detail = f"AI extracting text from {normalized_name}..."
                self._set_upload_pipeline_progress(file_idx, "extracting")
                yield
                extraction_result = await run_upload_extraction(
                    ExtractionRequest(
                        filename=file.filename,
                        content_type=getattr(file, "content_type", None),
                        file_bytes=file_bytes,
                        storage_folder=target_folder,
                    )
                )

                if extraction_result.status == "failed":
                    self.upload_error = (
                        f"Upload succeeded but extraction failed for '{file.filename}': {extraction_result.error}"
                    )
                elif extraction_result.text:
                    file_key = f"{target_folder}/{normalized_name}"
                    self.upload_stage = "indexing"
                    self.upload_stage_detail = f"AI indexing {normalized_name} for search..."
                    self._set_upload_pipeline_progress(file_idx, "indexing")
                    yield
                    enqueue_uploaded_document(
                        IndexingRequest(
                            file_key=file_key,
                            folder=target_folder,
                            filename=file.filename,
                            extracted_text=extraction_result.text,
                            doc_type=(normalized_name.rsplit(".", 1)[-1].lower() if "." in normalized_name else "file"),
                        )
                    )

                self.upload_stage_detail = f"Receipt processed: {normalized_name}"
                self._set_upload_pipeline_progress(file_idx, "done")
                yield

            self.upload_stage = "finalizing"
            self.upload_stage_detail = "Refreshing file explorer..."
            self.upload_progress_pct = max(self.upload_progress_pct, 97)
            yield
            self._reload_folder_children(target_folder)
            if uploaded_names:
                self.select_child_file(uploaded_names[-1])
            else:
                self.upload_error = "No files selected for upload."
                yield rx.toast.warning(self.upload_error)
                return

            self.excluded_upload_names = []
            self.upload_queue_previews = []
            self._stash_clear_modal_files()
            self.show_queued_preview = False
            self.queued_preview_name = ""
            self.queued_preview_url = ""
            self.queued_preview_kind = ""
            self.queued_preview_pages = []
            self.show_upload_confirm = False
            self.show_panel_drop_confirm = False
            self.show_drop_overlay = False
            self.upload_progress_pct = 100
            yield rx.clear_selected_files(FILES_UPLOAD_ZONE_ID)
            yield rx.toast.success(f"Upload complete. Processed {len(uploaded_names)} receipt file(s).")
        except Exception as e:
            self.upload_error = f"Upload failed: {e}"
            self.show_upload_confirm = False
            self.show_panel_drop_confirm = False
            yield rx.toast.error(f"Upload failed: {e}")
        finally:
            self._reset_upload_loading_state()

    def exclude_upload_file(self, filename: str) -> None:
        """Mark selected file to be skipped on upload."""
        if filename not in self.excluded_upload_names:
            self.excluded_upload_names.append(filename)

    def include_upload_file(self, filename: str) -> None:
        """Unskip file and include it again in upload."""
        self.excluded_upload_names = [name for name in self.excluded_upload_names if name != filename]

    def clear_removed_upload_files(self) -> None:
        """Restore all previously removed files back to the upload queue."""
        self.excluded_upload_names = []

    def open_queued_file_preview(self, filename: str) -> None:
        """Open queued preview modal for supported pre-upload types (image/pdf)."""
        self.queued_preview_name = filename
        match = next((row for row in self.upload_queue_previews if row.get("name", "") == filename), None)
        if not match:
            return
        preview_kind = str(match.get("preview_kind", ""))
        if preview_kind not in {"image", "pdf", "pdf_image"}:
            return
        self.queued_preview_kind = preview_kind
        self.queued_preview_url = str(match.get("preview_url", ""))
        self.queued_preview_pages = list(self.upload_queue_pdf_pages.get(filename, []))
        if self.queued_preview_url == "":
            self.upload_error = f"Preview unavailable for '{filename}'."
            return
        self.show_queued_preview = True

    def open_queued_image_preview(self, filename: str) -> None:
        """Backward-compatible alias for queued preview action."""
        return self.open_queued_file_preview(filename)

    def close_queued_image_preview(self) -> None:
        """Close queued image preview modal."""
        self.show_queued_preview = False
        self.queued_preview_name = ""
        self.queued_preview_url = ""
        self.queued_preview_kind = ""
        self.queued_preview_pages = []

    async def cache_upload_previews(self, files: list[rx.UploadFile]) -> None:
        """Build queue preview URLs from dropped/selected files (before upload)."""
        previews: list[dict[str, str]] = []
        pdf_pages_map: dict[str, list[str]] = {}
        self._stash_set_modal_files(files)
        self.show_queued_preview = False
        self.queued_preview_name = ""
        self.queued_preview_url = ""
        self.queued_preview_kind = ""
        self.queued_preview_pages = []
        # Fresh selection should start with a clean active queue.
        self.excluded_upload_names = []
        for file in files:
            filename = str(getattr(file, "filename", "") or "").strip()
            if not filename:
                continue
            lowered = filename.lower()
            is_image = lowered.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"))
            is_pdf = lowered.endswith(".pdf")
            preview_url = ""
            preview_kind = "file"
            if is_image:
                try:
                    await file.seek(0)
                    file_bytes = await file.read()
                    await file.seek(0)
                    ext = lowered.rsplit(".", 1)[-1] if "." in lowered else "png"
                    if ext in {"jpg", "jpeg"}:
                        mime = "image/jpeg"
                    elif ext == "svg":
                        mime = "image/svg+xml"
                    else:
                        mime = f"image/{ext}"
                    encoded = base64.b64encode(file_bytes).decode("ascii")
                    preview_url = f"data:{mime};base64,{encoded}"
                    preview_kind = "image"
                except Exception:
                    preview_url = ""
                    is_image = False
            elif is_pdf:
                try:
                    await file.seek(0)
                    file_bytes = await file.read()
                    await file.seek(0)
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    if doc.page_count > 0:
                        page_urls: list[str] = []
                        total_pages = min(doc.page_count, 12)
                        for page_index in range(total_pages):
                            page = doc.load_page(page_index)
                            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                            png_bytes = pix.tobytes("png")
                            encoded = base64.b64encode(png_bytes).decode("ascii")
                            page_urls.append(f"data:image/png;base64,{encoded}")
                        preview_url = page_urls[0]
                        pdf_pages_map[filename] = page_urls
                        preview_kind = "pdf_image"
                    doc.close()
                except Exception:
                    preview_url = ""
                    preview_kind = "pdf"
            previews.append(
                {
                    "name": filename,
                    "is_image": "1" if is_image else "0",
                    "preview_kind": preview_kind,
                    "preview_url": preview_url,
                }
            )
        self.upload_queue_previews = previews
        self.upload_queue_pdf_pages = pdf_pages_map

    def clear_upload_selection(self):
        """Clear staged upload list and skipped markers."""
        self.excluded_upload_names = []
        self.upload_queue_previews = []
        self.upload_queue_pdf_pages = {}
        self._stash_clear_modal_files()
        self.show_queued_preview = False
        self.queued_preview_name = ""
        self.queued_preview_url = ""
        self.queued_preview_kind = ""
        self.queued_preview_pages = []
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
        start_loading: bool = True,
    ) -> rx.event.EventSpec | None:
        """Persist uploads to Wasabi for the expanded folder; clear the given upload zone when done."""
        if not self.expanded_folder_name:
            self.upload_error = "Please open a folder first."
            self.show_upload_confirm = False
            self.show_panel_drop_confirm = False
            self.show_drop_overlay = False
            if not start_loading:
                self._reset_upload_loading_state()
            return rx.toast.warning(self.upload_error)
        if not files:
            self.upload_error = "No files selected. Add files to the queue or drop them on the panel first."
            self.show_upload_confirm = False
            if not start_loading:
                self._reset_upload_loading_state()
            return rx.toast.warning(self.upload_error)

        excluded_lower = {name.lower() for name in self.excluded_upload_names} if use_skip_list else set()
        queued_files = [file for file in files if normalize_item_name(file.filename).lower() not in excluded_lower]

        if not queued_files:
            self.upload_error = "Walang ia-upload: pumili ng file o i-undo ang Removed."
            self.show_upload_confirm = False
            if not start_loading:
                self._reset_upload_loading_state()
            return rx.toast.warning(self.upload_error)

        # If loading wasn't pre-started, initialize it here (legacy path).
        self.show_upload_confirm = False
        self.show_panel_drop_confirm = False
        if start_loading:
            self.is_uploading = True
            self.upload_error = ""
            self.upload_progress_pct = 0
            self.upload_stage = "preparing"
            self.upload_stage_detail = "Validating receipt files..."
            self.upload_completed_files = 0
        self.upload_total_files = len(queued_files)
        self.upload_progress_pct = 3

        try:
            storage = self._get_storage()
            target_folder = self._resolve_storage_folder_name(self.expanded_folder_name)
            uploaded_names: list[str] = []
            existing_names = {child["name"].lower() for child in self.active_folder_children}
            seen_batch: set[str] = set()

            for file_idx, file in enumerate(queued_files, start=1):
                validation_error = validate_upload_filename(file.filename)
                if validation_error:
                    self.upload_error = validation_error
                    return rx.toast.warning(self.upload_error)
                normalized_name = normalize_item_name(file.filename)
                lowered = normalized_name.lower()
                if lowered in existing_names:
                    self.upload_error = f"File '{normalized_name}' already exists in this folder."
                    return rx.toast.warning(self.upload_error)
                if lowered in seen_batch:
                    self.upload_error = f"Duplicate file in selection: '{normalized_name}'."
                    return rx.toast.warning(self.upload_error)
                seen_batch.add(lowered)

                self.upload_stage = "uploading"
                self.upload_stage_detail = (
                    f"Uploading receipt {normalized_name} ({file_idx}/{self.upload_total_files})..."
                )
                self._set_upload_pipeline_progress(file_idx, "uploading")
                await file.seek(0)
                file_bytes = await file.read()
                await file.seek(0)
                storage.upload_fileobj(target_folder, file.filename, file.file)
                uploaded_names.append(file.filename)

                self.upload_stage = "extracting"
                self.upload_stage_detail = f"AI extracting text from {normalized_name}..."
                self._set_upload_pipeline_progress(file_idx, "extracting")
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
                elif extraction_result.text:
                    file_key = f"{target_folder}/{normalized_name}"
                    self.upload_stage = "indexing"
                    self.upload_stage_detail = f"AI indexing {normalized_name} for search..."
                    self._set_upload_pipeline_progress(file_idx, "indexing")
                    enqueue_uploaded_document(
                        IndexingRequest(
                            file_key=file_key,
                            folder=target_folder,
                            filename=file.filename,
                            extracted_text=extraction_result.text,
                            doc_type=(normalized_name.rsplit(".", 1)[-1].lower() if "." in normalized_name else "file"),
                        )
                    )
                self.upload_completed_files = len(uploaded_names)
                self.upload_stage_detail = f"Receipt processed: {normalized_name}"
                self._set_upload_pipeline_progress(file_idx, "done")

            self.upload_stage = "finalizing"
            self.upload_stage_detail = "Refreshing file explorer..."
            self.upload_progress_pct = max(self.upload_progress_pct, 97)
            self._reload_folder_children(target_folder)
            if uploaded_names:
                self.select_child_file(uploaded_names[-1])
            else:
                self.upload_error = "No files selected for upload."
                return rx.toast.warning(self.upload_error)

            self.excluded_upload_names = []
            self.upload_queue_previews = []
            self.upload_queue_pdf_pages = {}
            self._stash_clear_modal_files()
            self.show_queued_preview = False
            self.queued_preview_name = ""
            self.queued_preview_url = ""
            self.queued_preview_kind = ""
            self.queued_preview_pages = []
            self.show_upload_confirm = False
            self.show_panel_drop_confirm = False
            self.show_drop_overlay = False
            self.upload_progress_pct = 100
            return [
                rx.clear_selected_files(clear_zone_id),
                rx.toast.success(f"Upload complete. Processed {len(uploaded_names)} receipt file(s)."),
            ]
        except Exception as e:
            self.upload_error = f"Upload failed: {e}"
            self.show_upload_confirm = False
            self.show_panel_drop_confirm = False
            return rx.toast.error(f"Upload failed: {e}")
        finally:
            self._reset_upload_loading_state()
