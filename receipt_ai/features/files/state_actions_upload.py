import base64
import json
import threading
import time

import fitz
import reflex as rx

from receipt_ai.core.upload_constants import (
    FILES_PANEL_UPLOAD_ZONE_ID,
    FILES_UPLOAD_ZONE_ID,
)
from receipt_ai.features.auth.state import AuthState
from receipt_ai.features.extraction.indexing import IndexingRequest
from receipt_ai.features.extraction.jobs import enqueue_uploaded_document
from receipt_ai.features.extraction.models import ExtractionRequest
from receipt_ai.features.extraction.orchestrator import run_upload_extraction
from receipt_ai.features.extraction.validators.image_receipt_validator import is_likely_receipt
from receipt_ai.features.files.validation import normalize_item_name, validate_upload_filename

# Process-local stash for UploadFile objects (cannot live in serialized Reflex state).
# Keys are per browser session + route so a follow-up handler tick can still read files
# after `confirm_upload_from_queue` chains to `run_confirmed_queue_upload`.
_MODAL_UPLOAD_FILES_BY_KEY: dict[str, list[rx.UploadFile]] = {}
_PANEL_UPLOAD_FILES_BY_KEY: dict[str, list[rx.UploadFile]] = {}
# Thread-safe cancel signal observed inside extraction (to_thread); pairs with upload_cancel_requested.
_UPLOAD_CANCEL_EVENTS_BY_KEY: dict[str, threading.Event] = {}
_PREVIEW_MAX_BYTES = 1_500_000
_PREVIEW_PDF_MAX_PAGES = 6
_DEBUG_LOG_PATH = "debug-fa7c0f.log"
_DEBUG_SESSION_ID = "fa7c0f"


def _agent_debug_log(location: str, message: str, data: dict, *, run_id: str, hypothesis_id: str) -> None:
    entry = {
        "sessionId": _DEBUG_SESSION_ID,
        "id": f"log_{time.time_ns()}",
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
    }
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


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
        self.upload_cancel_requested = False
        self.upload_stop_requested_at_ms = 0
        _UPLOAD_CANCEL_EVENTS_BY_KEY.pop(self._upload_stash_key(), None)
        self.upload_stage = ""
        self.upload_stage_detail = ""
        self.upload_total_files = 0
        self.upload_completed_files = 0
        self.upload_progress_pct = 0

    def _begin_upload_loading_state(self, total_files: int = 0) -> None:
        """Shared upload loading initializer so all flows use one pattern."""
        self.is_uploading = True
        self.upload_cancel_requested = False
        self.upload_stop_requested_at_ms = 0
        key = self._upload_stash_key()
        _UPLOAD_CANCEL_EVENTS_BY_KEY[key] = threading.Event()
        self.upload_error = ""
        self.upload_progress_pct = 0
        self.upload_stage = "preparing"
        self.upload_stage_detail = "Validating receipt files..."
        self.upload_completed_files = 0
        self.upload_total_files = max(0, int(total_files))

    def request_stop_upload(self) -> None:
        """Stop execution has been disabled for uploads."""
        return rx.toast.info("Stop execution is disabled for uploads.")

    def _upload_cancel_event_for_current_session(self) -> threading.Event | None:
        return _UPLOAD_CANCEL_EVENTS_BY_KEY.get(self._upload_stash_key())

    def _set_upload_pipeline_progress(self, file_idx: int, phase: str) -> None:
        """Set flow-based percent from real pipeline checkpoints."""
        total_files = max(1, int(self.upload_total_files))
        index = min(max(1, int(file_idx)), total_files)
        steps_per_file = 4  # extracting -> uploading -> indexing -> done
        phase_step = {
            "extracting": 1,
            "uploading": 2,
            "indexing": 3,
            "done": 4,
        }.get(phase, 0)
        completed_steps = ((index - 1) * steps_per_file) + phase_step
        total_steps = total_files * steps_per_file
        pct = int(round((completed_steps / total_steps) * 100))
        self.upload_progress_pct = max(self.upload_progress_pct, min(100, pct))

    def _upload_pipeline_outcome(
        self,
        status: str,
        *,
        flushes: int = 0,
        events: list[rx.event.EventSpec] | None = None,
    ) -> dict[str, object]:
        return {
            "status": status,
            "flushes": max(0, int(flushes)),
            "events": events or [],
        }

    async def _run_single_upload_pipeline_step(
        self,
        *,
        file_idx: int,
        file: rx.UploadFile,
        storage,
        target_folder: str,
        uploaded_names: list[str],
        existing_names: set[str],
        seen_batch: set[str],
        clear_zone_id: str,
        stream_updates: bool,
    ) -> dict[str, object]:
        flushes = 0
        normalized_name = normalize_item_name(file.filename)
        lowered = normalized_name.lower()
        # #region agent log
        _agent_debug_log(
            "state_actions_upload.py:_run_single_upload_pipeline_step:start",
            "Pipeline step start",
            {
                "file_idx": int(file_idx),
                "filename": str(file.filename),
                "upload_cancel_requested": bool(self.upload_cancel_requested),
                "stash_key": self._upload_stash_key(),
            },
            run_id="stop-debug",
            hypothesis_id="H3",
        )
        # #endregion

        def add_flush() -> None:
            nonlocal flushes
            if stream_updates:
                flushes += 1

        def cooperative_stop(message: str) -> dict[str, object]:
            self.upload_error = message
            self._reset_upload_loading_state()
            self._finalize_upload_session_after_cooperative_stop(target_folder, uploaded_names)
            return self._upload_pipeline_outcome(
                "stop",
                flushes=flushes,
                events=[rx.clear_selected_files(clear_zone_id), rx.toast.info(self.upload_error)],
            )

        if self.upload_cancel_requested:
            return cooperative_stop("Stop execution.")

        validation_error = validate_upload_filename(file.filename)
        if validation_error:
            self.upload_error = validation_error
            return self._upload_pipeline_outcome("warning", flushes=flushes, events=[rx.toast.warning(self.upload_error)])

        if lowered in existing_names:
            self.upload_error = f"File '{normalized_name}' already exists in this folder."
            return self._upload_pipeline_outcome("warning", flushes=flushes, events=[rx.toast.warning(self.upload_error)])
        if lowered in seen_batch:
            self.upload_error = f"Duplicate file in selection: '{normalized_name}'."
            return self._upload_pipeline_outcome("warning", flushes=flushes, events=[rx.toast.warning(self.upload_error)])
        seen_batch.add(lowered)

        await file.seek(0)
        file_bytes = await file.read()
        await file.seek(0)
        self.upload_stage = "extracting"
        self.upload_stage_detail = f"Validating receipt {normalized_name}..."
        self._set_upload_pipeline_progress(file_idx, "extracting")
        add_flush()

        if self.upload_cancel_requested:
            return cooperative_stop("Stop execution.")

        extraction_result = await run_upload_extraction(
            ExtractionRequest(
                filename=file.filename,
                content_type=getattr(file, "content_type", None),
                file_bytes=file_bytes,
                storage_folder=target_folder,
            )
        )
        # #region agent log
        _agent_debug_log(
            "state_actions_upload.py:_run_single_upload_pipeline_step:after_extraction",
            "Extraction returned",
            {
                "file_idx": int(file_idx),
                "filename": str(file.filename),
                "extraction_status": str(getattr(extraction_result, "status", "")),
                "upload_cancel_requested": bool(self.upload_cancel_requested),
            },
            run_id="stop-debug",
            hypothesis_id="H5",
        )
        # #endregion
        if extraction_result.status == "cancelled":
            return cooperative_stop("Stop execution.")
        if self.upload_cancel_requested:
            return cooperative_stop("Upload cancelled by user.")

        extracted_text = str(getattr(extraction_result, "text", "") or "").strip()
        if extraction_result.status == "failed":
            detail = str(getattr(extraction_result, "error", "") or "").strip()
            self.upload_error = (
                f"Upload failed for '{normalized_name}': {detail}"
                if detail
                else f"Upload failed for '{normalized_name}'."
            )
            self._reset_upload_loading_state()
            return self._upload_pipeline_outcome("warning", flushes=flushes, events=[rx.toast.warning(self.upload_error)])
        if not extracted_text or not is_likely_receipt(extracted_text):
            self.upload_error = f"Upload rejected: '{normalized_name}' is not a valid receipt."
            self._reset_upload_loading_state()
            return self._upload_pipeline_outcome("warning", flushes=flushes, events=[rx.toast.warning(self.upload_error)])

        self.upload_stage = "uploading"
        self.upload_stage_detail = f"Uploading receipt {normalized_name} ({file_idx}/{self.upload_total_files})..."
        self._set_upload_pipeline_progress(file_idx, "uploading")
        add_flush()
        if self.upload_cancel_requested:
            return cooperative_stop("Stop execution.")
        # #region agent log
        _agent_debug_log(
            "state_actions_upload.py:_run_single_upload_pipeline_step:before_upload_fileobj",
            "About to call storage.upload_fileobj",
            {
                "file_idx": int(file_idx),
                "filename": str(file.filename),
                "upload_cancel_requested": bool(self.upload_cancel_requested),
            },
            run_id="stop-debug",
            hypothesis_id="H4",
        )
        # #endregion
        storage.upload_fileobj(target_folder, file.filename, file.file)
        # #region agent log
        _agent_debug_log(
            "state_actions_upload.py:_run_single_upload_pipeline_step:after_upload_fileobj",
            "Returned from storage.upload_fileobj",
            {
                "file_idx": int(file_idx),
                "filename": str(file.filename),
                "upload_cancel_requested": bool(self.upload_cancel_requested),
            },
            run_id="stop-debug",
            hypothesis_id="H4",
        )
        # #endregion
        uploaded_names.append(file.filename)
        self.upload_completed_files = len(uploaded_names)
        add_flush()

        file_key = f"{target_folder}/{normalized_name}"
        self.upload_stage = "indexing"
        self.upload_stage_detail = f"AI indexing {normalized_name} for search..."
        self._set_upload_pipeline_progress(file_idx, "indexing")
        add_flush()
        if self.upload_cancel_requested:
            self._reject_non_receipt_after_upload(storage, target_folder, normalized_name)
            if uploaded_names and uploaded_names[-1] == file.filename:
                uploaded_names.pop()
            return cooperative_stop("Stop execution.")
        enqueue_uploaded_document(
            IndexingRequest(
                file_key=file_key,
                folder=target_folder,
                filename=file.filename,
                extracted_text=extracted_text,
                doc_type=(normalized_name.rsplit(".", 1)[-1].lower() if "." in normalized_name else "file"),
            )
        )

        self.upload_stage_detail = f"Receipt processed: {normalized_name}"
        self._set_upload_pipeline_progress(file_idx, "done")
        add_flush()
        return self._upload_pipeline_outcome("continue", flushes=flushes)

    def _reject_non_receipt_after_upload(self, storage, folder: str, filename: str) -> None:
        """Remove uploaded object when receipt validation fails."""
        try:
            storage.delete_object(f"{folder}/{filename}")
        except Exception:
            # Keep original rejection reason as the user-facing error.
            pass

    def _finalize_upload_session_after_cooperative_stop(self, target_folder: str, uploaded_names: list[str]) -> None:
        """Refresh explorer for files already completed; tear down modal queue (matches success-path cleanup)."""
        if uploaded_names:
            self._reload_folder_children(target_folder)
            self.select_child_file(uploaded_names[-1])
        self.show_drop_overlay = False
        self.show_upload_confirm = False
        self.show_panel_drop_confirm = False
        self.excluded_upload_names = []
        self.upload_queue_previews = []
        self.upload_queue_pdf_pages = {}
        self._stash_clear_modal_files()
        self.show_queued_preview = False
        self.queued_preview_name = ""
        self.queued_preview_url = ""
        self.queued_preview_kind = ""
        self.queued_preview_pages = []

    def _stash_set_modal_files(self, files: list[rx.UploadFile]) -> None:
        """Store modal UploadFile objects outside declared state (not serialized)."""
        _MODAL_UPLOAD_FILES_BY_KEY[self._upload_stash_key()] = list(files)

    def _stash_clear_modal_files(self) -> None:
        _MODAL_UPLOAD_FILES_BY_KEY.pop(self._upload_stash_key(), None)

    def _stash_set_panel_files(self, files: list[rx.UploadFile]) -> None:
        _PANEL_UPLOAD_FILES_BY_KEY[self._upload_stash_key()] = list(files)

    def _stash_clear_panel_files(self) -> None:
        _PANEL_UPLOAD_FILES_BY_KEY.pop(self._upload_stash_key(), None)

    async def _ensure_files_write_permission(self) -> bool:
        auth = await self.get_state(AuthState)
        if auth.has_permission("files:write"):
            return True
        self.upload_error = "Access denied: admin Files write access is required."
        return False

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
        self._begin_upload_loading_state(0)
        # Step 2: continue upload in next event tick.
        return type(self).run_confirmed_queue_upload

    async def run_confirmed_queue_upload(self):
        """Execute modal upload with streamed UI updates (progress + stage text)."""
        if not await self._ensure_files_write_permission():
            self._reset_upload_loading_state()
            yield rx.toast.error(self.upload_error)
            return
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
        self.upload_progress_pct = 0
        yield

        try:
            storage = self._get_storage()
            target_folder = self._resolve_storage_folder_name(self.expanded_folder_name)
            uploaded_names: list[str] = []
            existing_names = {child["name"].lower() for child in self.active_folder_children}
            seen_batch: set[str] = set()

            for file_idx, file in enumerate(queued_files, start=1):
                normalized_name = normalize_item_name(file.filename)
                lowered = normalized_name.lower()
                if self.upload_cancel_requested:
                    self.upload_error = "Stop execution."
                    self._reset_upload_loading_state()
                    self._finalize_upload_session_after_cooperative_stop(target_folder, uploaded_names)
                    yield rx.clear_selected_files(FILES_UPLOAD_ZONE_ID)
                    yield rx.toast.info(self.upload_error)
                    return
                validation_error = validate_upload_filename(file.filename)
                if validation_error:
                    self.upload_error = validation_error
                    self._reset_upload_loading_state()
                    yield
                    yield rx.toast.warning(self.upload_error)
                    return
                if lowered in existing_names:
                    self.upload_error = f"File '{normalized_name}' already exists in this folder."
                    self._reset_upload_loading_state()
                    yield
                    yield rx.toast.warning(self.upload_error)
                    return
                if lowered in seen_batch:
                    self.upload_error = f"Duplicate file in selection: '{normalized_name}'."
                    self._reset_upload_loading_state()
                    yield
                    yield rx.toast.warning(self.upload_error)
                    return
                seen_batch.add(lowered)

                await file.seek(0)
                file_bytes = await file.read()
                await file.seek(0)
                self.upload_stage = "extracting"
                self.upload_stage_detail = f"Validating receipt {normalized_name}..."
                self._set_upload_pipeline_progress(file_idx, "extracting")
                yield
                if self.upload_cancel_requested:
                    self.upload_error = "Stop execution."
                    self._reset_upload_loading_state()
                    self._finalize_upload_session_after_cooperative_stop(target_folder, uploaded_names)
                    yield rx.clear_selected_files(FILES_UPLOAD_ZONE_ID)
                    yield rx.toast.info(self.upload_error)
                    return
                extraction_result = await run_upload_extraction(
                    ExtractionRequest(
                        filename=file.filename,
                        content_type=getattr(file, "content_type", None),
                        file_bytes=file_bytes,
                        storage_folder=target_folder,
                    )
                )
                # #region agent log
                _agent_debug_log(
                    "state_actions_upload.py:run_confirmed_queue_upload:after_extraction",
                    "Extraction returned",
                    {
                        "file_idx": int(file_idx),
                        "filename": str(file.filename),
                        "extraction_status": str(getattr(extraction_result, "status", "")),
                        "upload_cancel_requested": bool(self.upload_cancel_requested),
                    },
                    run_id="stop-debug",
                    hypothesis_id="H5",
                )
                # #endregion
                if extraction_result.status == "cancelled":
                    self.upload_error = "Stop execution."
                    self._reset_upload_loading_state()
                    self._finalize_upload_session_after_cooperative_stop(target_folder, uploaded_names)
                    yield rx.clear_selected_files(FILES_UPLOAD_ZONE_ID)
                    yield rx.toast.info(self.upload_error)
                    return
                if self.upload_cancel_requested:
                    self.upload_error = "Upload cancelled by user."
                    self._reset_upload_loading_state()
                    self._finalize_upload_session_after_cooperative_stop(target_folder, uploaded_names)
                    yield rx.clear_selected_files(FILES_UPLOAD_ZONE_ID)
                    yield rx.toast.info(self.upload_error)
                    return

                extracted_text = str(getattr(extraction_result, "text", "") or "").strip()
                if extraction_result.status == "failed":
                    detail = str(getattr(extraction_result, "error", "") or "").strip()
                    self.upload_error = (
                        f"Upload failed for '{normalized_name}': {detail}"
                        if detail
                        else f"Upload failed for '{normalized_name}'."
                    )
                    self._reset_upload_loading_state()
                    yield
                    yield rx.toast.warning(self.upload_error)
                    return
                if not extracted_text or not is_likely_receipt(extracted_text):
                    self.upload_error = f"Upload rejected: '{normalized_name}' is not a valid receipt."
                    self._reset_upload_loading_state()
                    yield
                    yield rx.toast.warning(self.upload_error)
                    return

                self.upload_stage = "uploading"
                self.upload_stage_detail = f"Uploading receipt {normalized_name} ({file_idx}/{self.upload_total_files})..."
                self._set_upload_pipeline_progress(file_idx, "uploading")
                yield
                if self.upload_cancel_requested:
                    self.upload_error = "Stop execution."
                    self._reset_upload_loading_state()
                    self._finalize_upload_session_after_cooperative_stop(target_folder, uploaded_names)
                    yield rx.clear_selected_files(FILES_UPLOAD_ZONE_ID)
                    yield rx.toast.info(self.upload_error)
                    return
                # #region agent log
                _agent_debug_log(
                    "state_actions_upload.py:run_confirmed_queue_upload:before_upload_fileobj",
                    "About to call storage.upload_fileobj",
                    {
                        "file_idx": int(file_idx),
                        "filename": str(file.filename),
                        "upload_cancel_requested": bool(self.upload_cancel_requested),
                    },
                    run_id="stop-debug",
                    hypothesis_id="H4",
                )
                # #endregion
                storage.upload_fileobj(target_folder, file.filename, file.file)
                # #region agent log
                _agent_debug_log(
                    "state_actions_upload.py:run_confirmed_queue_upload:after_upload_fileobj",
                    "Returned from storage.upload_fileobj",
                    {
                        "file_idx": int(file_idx),
                        "filename": str(file.filename),
                        "upload_cancel_requested": bool(self.upload_cancel_requested),
                    },
                    run_id="stop-debug",
                    hypothesis_id="H4",
                )
                # #endregion
                uploaded_names.append(file.filename)
                self.upload_completed_files = len(uploaded_names)
                yield

                file_key = f"{target_folder}/{normalized_name}"
                self.upload_stage = "indexing"
                self.upload_stage_detail = f"AI indexing {normalized_name} for search..."
                self._set_upload_pipeline_progress(file_idx, "indexing")
                yield
                if self.upload_cancel_requested:
                    self._reject_non_receipt_after_upload(storage, target_folder, normalized_name)
                    if uploaded_names and uploaded_names[-1] == file.filename:
                        uploaded_names.pop()
                    self.upload_error = "Stop execution."
                    self._reset_upload_loading_state()
                    self._finalize_upload_session_after_cooperative_stop(target_folder, uploaded_names)
                    yield rx.clear_selected_files(FILES_UPLOAD_ZONE_ID)
                    yield rx.toast.info(self.upload_error)
                    return
                enqueue_uploaded_document(
                    IndexingRequest(
                        file_key=file_key,
                        folder=target_folder,
                        filename=file.filename,
                        extracted_text=extracted_text,
                        doc_type=(normalized_name.rsplit(".", 1)[-1].lower() if "." in normalized_name else "file"),
                    )
                )
                self.upload_stage_detail = f"Receipt processed: {normalized_name}"
                self._set_upload_pipeline_progress(file_idx, "done")
                yield

            self.upload_stage = "finalizing"
            self.upload_stage_detail = "Refreshing file explorer..."
            self.upload_progress_pct = max(self.upload_progress_pct, 99)
            yield
            self._reload_folder_children(target_folder)
            if uploaded_names:
                self.select_child_file(uploaded_names[-1])
            else:
                self.upload_error = "No files selected for upload."
                self._reset_upload_loading_state()
                yield
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
            self._reset_upload_loading_state()
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
            is_image = lowered.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"))
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
                    else:
                        mime = f"image/{ext}"
                    limited_bytes = file_bytes if len(file_bytes) <= _PREVIEW_MAX_BYTES else file_bytes[:_PREVIEW_MAX_BYTES]
                    encoded = base64.b64encode(limited_bytes).decode("ascii")
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
                        total_pages = min(doc.page_count, _PREVIEW_PDF_MAX_PAGES)
                        for page_index in range(total_pages):
                            page = doc.load_page(page_index)
                            pix = page.get_pixmap(matrix=fitz.Matrix(1.1, 1.1), alpha=False)
                            png_bytes = pix.tobytes("png")
                            limited_png = png_bytes if len(png_bytes) <= _PREVIEW_MAX_BYTES else png_bytes[:_PREVIEW_MAX_BYTES]
                            encoded = base64.b64encode(limited_png).decode("ascii")
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
        if not await self._ensure_files_write_permission():
            return rx.toast.error(self.upload_error)
        return await self._upload_to_open_folder(files, FILES_PANEL_UPLOAD_ZONE_ID, use_skip_list=False)

    async def upload_files(self, files: list[rx.UploadFile]) -> rx.event.EventSpec | None:
        """Upload from modal queue after confirmation (honours excluded_upload_names)."""
        if not await self._ensure_files_write_permission():
            return rx.toast.error(self.upload_error)
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
            self._begin_upload_loading_state(len(queued_files))
        self.upload_total_files = len(queued_files)
        self.upload_progress_pct = 0

        try:
            storage = self._get_storage()
            target_folder = self._resolve_storage_folder_name(self.expanded_folder_name)
            uploaded_names: list[str] = []
            existing_names = {child["name"].lower() for child in self.active_folder_children}
            seen_batch: set[str] = set()

            for file_idx, file in enumerate(queued_files, start=1):
                step_result = await self._run_single_upload_pipeline_step(
                    file_idx=file_idx,
                    file=file,
                    storage=storage,
                    target_folder=target_folder,
                    uploaded_names=uploaded_names,
                    existing_names=existing_names,
                    seen_batch=seen_batch,
                    clear_zone_id=clear_zone_id,
                    stream_updates=False,
                )
                if step_result["status"] != "continue":
                    events = list(step_result["events"])
                    if len(events) == 1:
                        return events[0]
                    return events

            self.upload_stage = "finalizing"
            self.upload_stage_detail = "Refreshing file explorer..."
            self.upload_progress_pct = max(self.upload_progress_pct, 99)
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
