import asyncio
import base64
import json
import time
import reflex as rx
from typing import Any

from receipt_ai.core.upload_constants import CHAT_UPLOAD_ZONE_ID
from receipt_ai.features.auth.state import AuthState
from receipt_ai.features.chat.rag_service import RagReply, stream_iter_next, stream_rag_chunks
from receipt_ai.features.chat.service import (
    append_assistant_message,
    append_message,
    create_conversation,
    delete_conversation,
    list_chat_payload,
    list_conversation_messages,
    list_message_feedback_map,
    list_message_sources_for_user,
    rename_conversation,
    update_assistant_message,
    update_user_message_content,
    upsert_message_feedback,
)
from receipt_ai.features.chat.suggestions import build_hybrid_suggestions
from receipt_ai.features.extraction.models import ExtractionRequest
from receipt_ai.features.extraction.orchestrator import run_upload_extraction
from receipt_ai.features.files.validation import validate_upload_filename
from receipt_ai.features.files.state import FilesState, get_storage

# History rail drag: same pattern as Files explorer (rx.call_script + Promise).
_CHAT_DIVIDER_DRAG_JS = """
return new Promise((resolve) => {
  const root = document.getElementById("chat-split-root");
  if (!root) {
    resolve(22);
    return;
  }
  const prevSelect = document.body.style.userSelect;
  document.body.style.userSelect = "none";
  const move = (e) => {
    const r = root.getBoundingClientRect();
    if (r.width <= 0) return;
    let p = ((e.clientX - r.left) / r.width) * 100;
    p = Math.max(15, Math.min(48, p));
    root.style.setProperty("--chat-sidebar-pct", p + "%");
  };
  const up = () => {
    window.removeEventListener("mousemove", move);
    document.body.style.userSelect = prevSelect;
    const raw = getComputedStyle(root).getPropertyValue("--chat-sidebar-pct").trim() || "22%";
    const n = parseFloat(raw);
    resolve(Number.isFinite(n) ? Math.round(n) : 22);
  };
  window.addEventListener("mousemove", move);
  window.addEventListener("mouseup", up, { once: true });
});
"""

_CHAT_UPLOAD_FILES_BY_KEY: dict[str, list[rx.UploadFile]] = {}


class ChatState(rx.State):
    """State container for chat feature."""

    sidebar_threads: list[dict[str, str]] = []
    active_conversation_id: str = ""
    # Each turn: {"role": "user" | "assistant", "content": str} (assistant uses markdown when needed).
    messages: list[dict[str, Any]] = []
    draft_message: str = ""
    rag_busy: bool = False
    streaming_text: str = ""
    streaming_mode: str = "normal"
    chat_mode: str = "normal"
    last_failed_prompt: str = ""
    last_failed_mode: str = "normal"
    last_failed_folder_key: str = ""
    last_failed_file_key: str = ""

    chat_sidebar_width_pct: int = 22
    chat_mobile_view: str = "history"
    show_new_chat_confirm: bool = False
    show_delete_chat_confirm: bool = False
    pending_delete_conversation_id: str = ""
    chat_upload_previews: list[dict[str, str]] = []
    chat_upload_error: str = ""
    show_chat_image_preview: bool = False
    chat_preview_name: str = ""
    chat_preview_url: str = ""
    chat_preview_images: list[dict[str, str]] = []
    chat_preview_index: int = 0
    suggested_prompts: list[str] = []
    message_action_role: str = ""
    message_action_index: int = -1
    message_action_label: str = ""
    cancel_stream_requested: bool = False
    last_user_prompt: str = ""
    last_user_mode: str = "normal"
    last_user_folder_key: str = ""
    last_user_file_key: str = ""
    message_feedback: dict[str, str] = {}
    editing_message_id: str = ""
    editing_message_index: int = -1
    last_failed_assistant_message_id: str = ""

    @rx.var
    def chat_sidebar_width_css(self) -> str:
        return f"{self.chat_sidebar_width_pct}%"

    @rx.var
    def has_messages(self) -> bool:
        return len(self.messages) > 0

    @rx.var
    def can_send(self) -> bool:
        return ((self.draft_message or "").strip() != "" or self.has_queued_attachments) and not self.rag_busy

    @rx.var
    def has_queued_attachments(self) -> bool:
        return len(self._stash_get_chat_files()) > 0

    @rx.var
    def show_suggestions(self) -> bool:
        return (not self.has_messages) and (not self.rag_busy) and len(self.suggested_prompts) > 0

    @rx.var
    def chat_preview_has_prev(self) -> bool:
        return self.chat_preview_index > 0

    @rx.var
    def chat_preview_has_next(self) -> bool:
        return self.chat_preview_index < max(0, len(self.chat_preview_images) - 1)

    @rx.var
    def thinking_enabled(self) -> bool:
        return self.chat_mode == "reasoning"

    @rx.var
    def message_count(self) -> int:
        return len(self.messages)

    @rx.var
    def recent_messages(self) -> list[str]:
        """Short previews for the Recent column (Technical AI–style snippets)."""
        if not self.messages:
            return []
        previews: list[str] = []
        for row in self.messages[-6:]:
            if not isinstance(row, dict):
                continue
            text = str(row.get("content", "")).strip().replace("\n", " ")
            if len(text) > 72:
                text = text[:69] + "…"
            role = row.get("role", "user")
            prefix = "You: " if role == "user" else "AI: "
            if text:
                previews.append(prefix + text)
        return previews

    def _upload_stash_key(self) -> str:
        router = getattr(self, "router_data", None)
        session = getattr(router, "session", None) if router is not None else None
        token = str(getattr(session, "client_token", "") or "").strip()
        sid = str(getattr(session, "session_id", "") or "").strip()
        route = str(getattr(router, "route_id", "") or "").strip() if router is not None else ""
        base = token or sid
        if base:
            return f"{base}:{route}" if route else base
        return f"chat-state:{id(self)}"

    def _new_local_message_id(self, prefix: str) -> str:
        stamp = int(time.time() * 1000)
        return f"{prefix}-{stamp}-{len(self.messages)}"

    def _stash_set_chat_files(self, files: list[rx.UploadFile]) -> None:
        _CHAT_UPLOAD_FILES_BY_KEY[self._upload_stash_key()] = list(files)

    def _stash_get_chat_files(self) -> list[rx.UploadFile]:
        return list(_CHAT_UPLOAD_FILES_BY_KEY.get(self._upload_stash_key(), []))

    def _stash_clear_chat_files(self) -> None:
        _CHAT_UPLOAD_FILES_BY_KEY.pop(self._upload_stash_key(), None)

    async def cache_chat_upload_previews(self, files: list[rx.UploadFile]) -> None:
        """Build local image previews for chat attachments (user-only)."""
        auth = await self.get_state(AuthState)
        if not auth.is_standard_user or not auth.can_chat_image_upload:
            self.chat_upload_error = "Chat attachment upload is available for user role only."
            self.chat_upload_previews = []
            self._stash_clear_chat_files()
            return
        previews: list[dict[str, str]] = []
        filtered_files: list[rx.UploadFile] = []
        self.chat_upload_error = ""
        for file in files[:3]:
            filename = str(getattr(file, "filename", "") or "").strip()
            if not filename:
                continue
            validation_error = validate_upload_filename(filename)
            if validation_error:
                self.chat_upload_error = validation_error
                continue
            lowered = filename.lower()
            if not lowered.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".jfif")):
                self.chat_upload_error = "Only image files are supported in chat attachments."
                continue
            try:
                await file.seek(0)
                file_bytes = await file.read()
                await file.seek(0)
                ext = lowered.rsplit(".", 1)[-1] if "." in lowered else "png"
                mime = "image/jpeg" if ext in {"jpg", "jpeg", "jfif"} else f"image/{ext}"
                encoded = base64.b64encode(file_bytes).decode("ascii")
                preview_url = f"data:{mime};base64,{encoded}"
                previews.append({"name": filename, "preview_url": preview_url})
                filtered_files.append(file)
            except Exception:
                self.chat_upload_error = f"Preview unavailable for '{filename}'."
        self.chat_upload_previews = previews
        if filtered_files:
            self._stash_set_chat_files(filtered_files)
        else:
            self._stash_clear_chat_files()

    async def load_suggestions(self) -> None:
        files = await self.get_state(FilesState)
        auth = await self.get_state(AuthState)
        folder_name = str(getattr(files, "expanded_folder_name", "") or "")
        file_name = str(getattr(files, "selected_child_file_name", "") or "")
        self.suggested_prompts = build_hybrid_suggestions(
            folder_name=folder_name,
            file_name=file_name,
            role=str(getattr(auth, "primary_role", "user") or "user"),
        )

    def apply_suggestion(self, prompt: str) -> None:
        self.draft_message = (prompt or "").strip()

    def set_message_action_hint(self, role: str, index: int, label: str = "Copied") -> None:
        self.message_action_role = (role or "").strip().lower()
        try:
            self.message_action_index = int(index)
        except (TypeError, ValueError):
            self.message_action_index = -1
        self.message_action_label = (label or "").strip() or "Done"

    def clear_message_action_hint(self) -> None:
        self.message_action_role = ""
        self.message_action_index = -1
        self.message_action_label = ""

    def copy_message_action(self, text: str, role: str, index: int):
        payload = json.dumps(str(text or ""))
        self.set_message_action_hint(role, index, "Copied")
        return rx.call_script(
            f"if (navigator.clipboard && navigator.clipboard.writeText) {{ navigator.clipboard.writeText({payload}); }}"
        )

    def copy_markdown_stub(self, text: str, role: str, index: int):
        payload = json.dumps(str(text or ""))
        self.set_message_action_hint(role, index, "Markdown copied")
        return rx.call_script(
            f"if (navigator.clipboard && navigator.clipboard.writeText) {{ navigator.clipboard.writeText({payload}); }}"
        )

    def _build_citation_text(self, sources: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for source in sources:
            source_index = int(source.get("source_index", 0) or 0)
            source_name = str(source.get("source_name", "")).strip() or str(source.get("file_key", "")).strip() or "source"
            chunk_index = int(source.get("chunk_index", 0) or 0)
            score = float(source.get("score", 0.0) or 0.0)
            lines.append(
                f"Source {source_index}: {source_name} (chunk {chunk_index}, score {score:.3f})"
            )
        return "\n".join(lines).strip()

    async def open_message_source(self, message_id: str) -> rx.event.EventSpec:
        msg_id = (message_id or "").strip()
        if not msg_id:
            return rx.toast.warning("No source is available for this message.")
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            return rx.toast.error("Please sign in to open sources.")
        sources = await list_message_sources_for_user(msg_id, user_id=auth.user_id)
        if not sources:
            return rx.toast.warning("No source is available for this message.")
        file_key = str(sources[0].get("file_key", "")).strip()
        if not file_key:
            return rx.toast.warning("Source file is missing.")
        try:
            storage = get_storage()
            source_url = storage.presigned_get_url(file_key, inline=True)
            return rx.redirect(source_url, is_external=True)
        except Exception as exc:
            return rx.toast.error(f"Failed to open source: {exc}")

    async def copy_message_citation(self, message_id: str, role: str, index: int):
        msg_id = (message_id or "").strip()
        if not msg_id:
            return rx.toast.warning("No citation is available for this message.")
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            return rx.toast.error("Please sign in to copy citations.")
        sources = await list_message_sources_for_user(msg_id, user_id=auth.user_id)
        if not sources:
            return rx.toast.warning("No citation is available for this message.")
        payload = json.dumps(self._build_citation_text(sources[:3]))
        self.set_message_action_hint(role, index, "Citation copied")
        return rx.call_script(
            f"if (navigator.clipboard && navigator.clipboard.writeText) {{ navigator.clipboard.writeText({payload}); }}"
        )

    def share_message_stub(self) -> rx.event.EventSpec:
        return rx.toast.warning("Share action will be connected soon.")

    def export_message_stub(self) -> rx.event.EventSpec:
        return rx.toast.warning("Export action is not wired yet.")

    async def set_message_feedback(self, message_id: str, vote: str):
        key = (message_id or "").strip()
        value = (vote or "").strip().lower()
        if not key or value not in {"up", "down"}:
            return
        previous = self.message_feedback.get(key, "")
        self.messages = [
            {**row, "feedback_vote": (value if str(row.get("id", "")).strip() == key else row.get("feedback_vote", ""))}
            for row in self.messages
        ]
        self.message_feedback = {**self.message_feedback, key: value}
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            self.messages = [
                {**row, "feedback_vote": (previous if str(row.get("id", "")).strip() == key else row.get("feedback_vote", ""))}
                for row in self.messages
            ]
            self.message_feedback = {**self.message_feedback, key: previous} if previous else {
                k: v for (k, v) in self.message_feedback.items() if k != key
            }
            return rx.toast.error("Please sign in to save feedback.")
        ok = await upsert_message_feedback(message_id=key, user_id=auth.user_id, vote=value)
        if ok:
            return
        self.messages = [
            {**row, "feedback_vote": (previous if str(row.get("id", "")).strip() == key else row.get("feedback_vote", ""))}
            for row in self.messages
        ]
        self.message_feedback = {**self.message_feedback, key: previous} if previous else {
            k: v for (k, v) in self.message_feedback.items() if k != key
        }
        return rx.toast.error("Could not save feedback right now.")

    def edit_message_to_draft(self, text: str, message_id: str = "", index: int = -1) -> None:
        self.draft_message = str(text or "").strip()
        self.editing_message_id = str(message_id or "").strip()
        try:
            self.editing_message_index = int(index)
        except (TypeError, ValueError):
            self.editing_message_index = -1

    def resend_message_from_bubble(self, text: str):
        self.draft_message = str(text or "").strip()
        if self.draft_message == "":
            return None
        return type(self).send_draft

    def clear_chat_upload_selection(self):
        self.chat_upload_previews = []
        self.chat_upload_error = ""
        self.show_chat_image_preview = False
        self.chat_preview_name = ""
        self.chat_preview_url = ""
        self.chat_preview_images = []
        self.chat_preview_index = 0
        self._stash_clear_chat_files()
        return rx.clear_selected_files(CHAT_UPLOAD_ZONE_ID)

    def remove_chat_upload_preview(self, filename: str) -> None:
        """Remove one queued chat attachment by filename."""
        target = (filename or "").strip()
        if not target:
            return
        self.chat_upload_previews = [row for row in self.chat_upload_previews if row.get("name", "") != target]
        if self.chat_preview_name == target:
            self.show_chat_image_preview = False
            self.chat_preview_name = ""
            self.chat_preview_url = ""
            self.chat_preview_images = []
            self.chat_preview_index = 0
        keep = [f for f in self._stash_get_chat_files() if str(getattr(f, "filename", "") or "").strip() != target]
        if keep:
            self._stash_set_chat_files(keep)
        else:
            self._stash_clear_chat_files()

    def open_chat_image_preview(self, filename: str) -> None:
        target = (filename or "").strip()
        if not target:
            return
        images = [
            {
                "name": str(item.get("name", "")).strip(),
                "preview_url": str(item.get("preview_url", "")).strip(),
            }
            for item in self.chat_upload_previews
            if str(item.get("preview_url", "")).strip() != ""
        ]
        if not images:
            return
        row = next((item for item in images if item.get("name", "") == target), None)
        if not row:
            return
        preview_url = str(row.get("preview_url", "") or "").strip()
        if not preview_url:
            return
        self.chat_preview_images = images
        self.chat_preview_index = max(0, next((i for i, item in enumerate(images) if item.get("name", "") == target), 0))
        self.chat_preview_name = target
        self.chat_preview_url = preview_url
        self.show_chat_image_preview = True

    def open_message_image_preview(self, filename: str, preview_url: str) -> None:
        target = (filename or "").strip() or "Attachment"
        src = (preview_url or "").strip()
        if not src:
            return
        self.chat_preview_images = [{"name": target, "preview_url": src}]
        self.chat_preview_index = 0
        self.chat_preview_name = target
        self.chat_preview_url = src
        self.show_chat_image_preview = True

    def open_message_image_preview_group(
        self,
        index: int,
        name1: str,
        url1: str,
        name2: str = "",
        url2: str = "",
        name3: str = "",
        url3: str = "",
    ) -> None:
        images = [
            {"name": str(name1 or "").strip() or "Attachment", "preview_url": str(url1 or "").strip()},
            {"name": str(name2 or "").strip() or "Attachment", "preview_url": str(url2 or "").strip()},
            {"name": str(name3 or "").strip() or "Attachment", "preview_url": str(url3 or "").strip()},
        ]
        images = [row for row in images if row["preview_url"] != ""]
        if not images:
            return
        idx = max(0, min(len(images) - 1, int(index)))
        current = images[idx]
        self.chat_preview_images = images
        self.chat_preview_index = idx
        self.chat_preview_name = current["name"]
        self.chat_preview_url = current["preview_url"]
        self.show_chat_image_preview = True

    def close_chat_image_preview(self) -> None:
        self.show_chat_image_preview = False
        self.chat_preview_name = ""
        self.chat_preview_url = ""
        self.chat_preview_images = []
        self.chat_preview_index = 0

    def request_stop_generation(self) -> None:
        self.cancel_stream_requested = True

    def preview_next_image(self) -> None:
        if not self.chat_preview_images:
            return
        if self.chat_preview_index >= len(self.chat_preview_images) - 1:
            return
        self.chat_preview_index += 1
        row = self.chat_preview_images[self.chat_preview_index]
        self.chat_preview_name = str(row.get("name", "Attachment"))
        self.chat_preview_url = str(row.get("preview_url", ""))

    def preview_prev_image(self) -> None:
        if not self.chat_preview_images:
            return
        if self.chat_preview_index <= 0:
            return
        self.chat_preview_index -= 1
        row = self.chat_preview_images[self.chat_preview_index]
        self.chat_preview_name = str(row.get("name", "Attachment"))
        self.chat_preview_url = str(row.get("preview_url", ""))

    def handle_chat_preview_key_signal(self, signal: str):
        if signal == "close_preview":
            return type(self).close_chat_image_preview

    def _is_receipt_rejection_error(self, text: str) -> bool:
        msg = str(text or "").strip().lower()
        return (
            "not_receipt" in msg
            or "not a receipt" in msg
            or "does not look like a receipt" in msg
            or "receipt validation" in msg
        )

    async def _extract_chat_attachment_context(self) -> tuple[str, list[str], list[str]]:
        """Extract text from queued image attachments for prompt context.

        Returns: (joined_context, valid_receipt_names, rejected_non_receipt_names)
        """
        files = self._stash_get_chat_files()
        if not files:
            return ("", [], [])
        chunks: list[str] = []
        valid_names: list[str] = []
        rejected_names: list[str] = []
        for file in files[:3]:
            filename = str(getattr(file, "filename", "") or "").strip()
            if not filename:
                continue
            await file.seek(0)
            file_bytes = await file.read()
            await file.seek(0)
            result = await run_upload_extraction(
                ExtractionRequest(
                    filename=filename,
                    content_type=getattr(file, "content_type", None),
                    file_bytes=file_bytes,
                    storage_folder="chat_uploads",
                )
            )
            if result.status == "success" and result.text.strip():
                valid_names.append(filename)
                chunks.append(f"Attachment: {filename}\n{result.text.strip()}")
                continue
            if self._is_receipt_rejection_error(result.error):
                rejected_names.append(filename)
        if not chunks:
            return ("", valid_names, rejected_names)
        return ("\n\n".join(chunks), valid_names, rejected_names)

    async def load_history(self) -> None:
        auth = await self.get_state(AuthState)
        if not auth.user_id or not auth.has_permission("chat:read"):
            self.sidebar_threads = []
            self.active_conversation_id = ""
            self.messages = []
            self.message_feedback = {}
            self.streaming_text = ""
            await self.load_suggestions()
            return
        self.sidebar_threads = await list_chat_payload(auth.user_id)
        if not self.sidebar_threads:
            self.active_conversation_id = ""
            self.messages = []
            self.message_feedback = {}
            self.streaming_text = ""
            await self.load_suggestions()
            return
        if not self.active_conversation_id:
            self.active_conversation_id = str(self.sidebar_threads[0].get("id", ""))
        self.streaming_text = ""
        await self._load_active_conversation_messages()
        await self.load_suggestions()

    async def select_conversation(self, conversation_id: str) -> None:
        self.active_conversation_id = conversation_id
        self.streaming_text = ""
        await self._load_active_conversation_messages()

    def request_delete_thread(self, conversation_id: str) -> None:
        convo_id = (conversation_id or "").strip()
        if not convo_id:
            return
        self.pending_delete_conversation_id = convo_id
        self.show_delete_chat_confirm = True

    def cancel_delete_thread(self) -> None:
        self.show_delete_chat_confirm = False
        self.pending_delete_conversation_id = ""

    async def confirm_delete_thread(self) -> None:
        convo_id = (self.pending_delete_conversation_id or "").strip()
        self.show_delete_chat_confirm = False
        self.pending_delete_conversation_id = ""
        if not convo_id:
            return
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            return
        await delete_conversation(convo_id, user_id=auth.user_id)
        self.sidebar_threads = await list_chat_payload(auth.user_id)
        if self.active_conversation_id == convo_id:
            self.active_conversation_id = ""
            self.messages = []
            self.streaming_text = ""
            if self.sidebar_threads:
                self.active_conversation_id = str(self.sidebar_threads[0].get("id", ""))
                await self._load_active_conversation_messages()

    async def _load_active_conversation_messages(self) -> None:
        convo_id = (self.active_conversation_id or "").strip()
        if not convo_id:
            self.messages = []
            self.message_feedback = {}
            self.streaming_text = ""
            return
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            self.messages = []
            self.message_feedback = {}
            self.streaming_text = ""
            return
        loaded_messages = await list_conversation_messages(convo_id, user_id=auth.user_id)
        feedback_map = await list_message_feedback_map(convo_id, user_id=auth.user_id)
        self.message_feedback = feedback_map
        self.messages = [
            {
                **row,
                "feedback_vote": feedback_map.get(str(row.get("id", "")).strip(), ""),
            }
            for row in loaded_messages
        ]
        self.streaming_text = ""
        await self.load_suggestions()

    def set_draft(self, value: str) -> None:
        self.draft_message = value

    def set_chat_mode(self, value: str) -> None:
        mode = (value or "").strip().lower()
        if mode in {"normal", "reasoning"}:
            self.chat_mode = mode

    def toggle_thinking_mode(self) -> None:
        self.chat_mode = "normal" if self.chat_mode == "reasoning" else "reasoning"

    def _push_assistant_message(
        self,
        reply: RagReply,
        *,
        message_id: str = "",
        stopped_by_user: bool = False,
        replace_index: int = -1,
    ) -> None:
        sources_payload = [
            {
                "source_index": int(src.source_index),
                "file_key": src.file_key,
                "source_name": src.source_name,
                "chunk_index": int(src.chunk_index),
                "score": float(src.score),
            }
            for src in reply.sources
        ]
        source_file_count = len(
            {
                str(src.get("file_key", "")).strip()
                for src in sources_payload
                if str(src.get("file_key", "")).strip() != ""
            }
        )
        source_chunk_count = len(sources_payload)
        row = {
            "id": (message_id or self._new_local_message_id("assistant")),
            "role": "assistant",
            "content": reply.content,
            "mode": reply.mode,
            "is_error": "1" if reply.error else "0",
            "sources": sources_payload,
            "sources_count": len(sources_payload),
            "sources_file_count": source_file_count,
            "sources_chunk_count": source_chunk_count,
            "sources_preview": ", ".join(
                [f"Source {src['source_index']}: {src['source_name']}" for src in sources_payload[:2]]
            ),
            "stopped_by_user": "1" if stopped_by_user else "0",
            "feedback_vote": "",
        }
        if 0 <= int(replace_index) < len(self.messages):
            self.messages = [*self.messages[:replace_index], row, *self.messages[replace_index + 1 :]]
            return
        self.messages = [*self.messages, row]

    def scroll_chat_to_latest(self):
        return rx.call_script(
            "const el=document.getElementById('chat-thread-scroll');"
            "if(el){el.scrollTo({top:el.scrollHeight, behavior:'smooth'});}"
        )

    def handle_composer_key_signal(self, signal: str):
        if signal in {"send", "send_now"}:
            return type(self).send_draft

    async def send_draft(self):
        message = self.draft_message.strip()
        if (not message and not self.has_queued_attachments) or self.rag_busy:
            return
        clipped = message[:2000] if message else "Please analyze these attached receipt images."
        self.rag_busy = True
        self.cancel_stream_requested = False
        self.streaming_text = ""
        smode = (self.chat_mode or "normal").strip().lower()
        self.streaming_mode = smode if smode in {"normal", "reasoning"} else "normal"
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            self.rag_busy = False
            self.streaming_text = ""
            self.messages = [
                *self.messages,
                {
                "id": self._new_local_message_id("assistant"),
                    "role": "assistant",
                    "content": "Please sign in first.",
                    "mode": "normal",
                    "is_error": "1",
                    "sources": [],
                    "sources_count": 0,
                    "sources_preview": "",
                },
            ]
            yield self.scroll_chat_to_latest()
            return
        if not auth.has_permission("chat:write"):
            self.rag_busy = False
            self.streaming_text = ""
            self.messages = [
                *self.messages,
                {
                "id": self._new_local_message_id("assistant"),
                    "role": "assistant",
                    "content": "Access denied: chat write permission is required.",
                    "mode": "normal",
                    "is_error": "1",
                    "sources": [],
                    "sources_count": 0,
                    "sources_preview": "",
                },
            ]
            yield self.scroll_chat_to_latest()
            return
        if self._stash_get_chat_files() and (not auth.is_standard_user or not auth.can_chat_image_upload):
            self.rag_busy = False
            self.streaming_text = ""
            self.messages = [
                *self.messages,
                {
                "id": self._new_local_message_id("assistant"),
                    "role": "assistant",
                    "content": "Access denied: chat image upload permission is required.",
                    "mode": "normal",
                    "is_error": "1",
                    "sources": [],
                    "sources_count": 0,
                    "sources_preview": "",
                },
            ]
            yield self.scroll_chat_to_latest()
            return

        attachment_context, attachment_names, rejected_attachment_names = await self._extract_chat_attachment_context()
        request_message = clipped
        if attachment_context:
            request_message = f"{clipped}\n\n[Attached image extraction context]\n{attachment_context}"
        ui_message = clipped
        if attachment_names:
            ui_message = f"{clipped}\n\n[Attached: {', '.join(attachment_names)}]"

        if not self.active_conversation_id:
            self.active_conversation_id = await create_conversation(auth.user_id, title=clipped[:80])
            self.sidebar_threads = await list_chat_payload(auth.user_id)

        attachments_payload = [
            {"name": row.get("name", ""), "preview_url": row.get("preview_url", "")}
            for row in self.chat_upload_previews
            if (
                str(row.get("preview_url", "") or "").strip() != ""
                and str(row.get("name", "") or "").strip() in set(attachment_names)
            )
        ]
        edit_message_id = (self.editing_message_id or "").strip()
        edit_index = int(self.editing_message_index) if self.editing_message_index >= 0 else -1
        response_replace_index = -1
        response_replace_id = ""

        if edit_message_id:
            if not attachments_payload and 0 <= edit_index < len(self.messages):
                existing = self.messages[edit_index]
                if str(existing.get("id", "")).strip() == edit_message_id:
                    attachments_payload = list(existing.get("attachments_list", []))
            updated = await update_user_message_content(
                message_id=edit_message_id,
                user_id=auth.user_id,
                content=ui_message,
                attachments=attachments_payload,
            )
            if updated:
                if 0 <= edit_index < len(self.messages):
                    target = self.messages[edit_index]
                    if str(target.get("id", "")).strip() == edit_message_id:
                        self.messages = [
                            *self.messages[:edit_index],
                            {
                                **target,
                                "content": ui_message,
                                "attachments": attachments_payload,
                                "attachments_count": len(attachments_payload),
                                "attachments_more_label": (f"+{len(attachments_payload) - 1} more" if len(attachments_payload) > 1 else ""),
                                "attachments_list": attachments_payload,
                            },
                            *self.messages[edit_index + 1 :],
                        ]
                for j in range(edit_index + 1, len(self.messages)):
                    if str(self.messages[j].get("role", "")) == "assistant":
                        response_replace_index = j
                        response_replace_id = str(self.messages[j].get("id", "")).strip()
                        break
            else:
                edit_message_id = ""
                self.editing_message_id = ""
                self.editing_message_index = -1

        if not edit_message_id:
            created_user_message_id = await append_message(
                self.active_conversation_id,
                user_id=auth.user_id,
                role="user",
                content=ui_message,
                attachments=attachments_payload,
            )
            self.messages = [
                *self.messages,
                {
                    "id": (created_user_message_id or self._new_local_message_id("user")),
                    "role": "user",
                    "content": ui_message,
                    "sources": [],
                    "sources_count": 0,
                    "sources_preview": "",
                    "attachments": attachments_payload,
                    "attachments_count": len(attachments_payload),
                    "attachments_more_label": (f"+{len(attachments_payload) - 1} more" if len(attachments_payload) > 1 else ""),
                    "attachments_list": attachments_payload,
                    "attachment_name_1": (str(attachments_payload[0].get("name", "")).strip() if len(attachments_payload) > 0 else ""),
                    "attachment_preview_url_1": (
                        str(attachments_payload[0].get("preview_url", "")).strip() if len(attachments_payload) > 0 else ""
                    ),
                    "attachment_name_2": (str(attachments_payload[1].get("name", "")).strip() if len(attachments_payload) > 1 else ""),
                    "attachment_preview_url_2": (
                        str(attachments_payload[1].get("preview_url", "")).strip() if len(attachments_payload) > 1 else ""
                    ),
                    "attachment_name_3": (str(attachments_payload[2].get("name", "")).strip() if len(attachments_payload) > 2 else ""),
                    "attachment_preview_url_3": (
                        str(attachments_payload[2].get("preview_url", "")).strip() if len(attachments_payload) > 2 else ""
                    ),
                    "attachment_name": (
                        str(attachments_payload[0].get("name", "")).strip() if attachments_payload else ""
                    ),
                    "attachment_preview_url": (
                        str(attachments_payload[0].get("preview_url", "")).strip() if attachments_payload else ""
                    ),
                },
            ]
        self.draft_message = ""
        self.editing_message_id = ""
        self.editing_message_index = -1
        try:
            yield
            # If attachments were provided but none were accepted as receipts, short-circuit with fallback.
            if self.has_queued_attachments and not attachment_names and rejected_attachment_names:
                fallback = (
                    "I can only process receipt images. "
                    "Please upload a clear photo or scan of an official receipt."
                )
                assistant_message_id = await append_assistant_message(
                    self.active_conversation_id,
                    user_id=auth.user_id,
                    content=fallback,
                    sources=[],
                )
                self._push_assistant_message(
                    RagReply(content=fallback, mode=self.chat_mode, sources=[], error="", retryable=False),
                    message_id=assistant_message_id,
                    stopped_by_user=False,
                    replace_index=response_replace_index if assistant_message_id == response_replace_id else -1,
                )
                self.last_failed_prompt = ""
                self.last_failed_mode = "normal"
                self.last_failed_folder_key = ""
                self.last_failed_file_key = ""
                self.last_failed_assistant_message_id = ""
                yield self.scroll_chat_to_latest()
                return

            files = await self.get_state(FilesState)
            folder_key = None
            file_exact = None
            if files.expanded_folder_name:
                folder_key = files._resolve_storage_folder_name(files.expanded_folder_name)
                if files.selected_child_file_name:
                    file_exact = f"{folder_key}/{files.selected_child_file_name}"
            mode = self.chat_mode
            self.last_user_prompt = request_message
            self.last_user_mode = mode
            self.last_user_folder_key = folder_key or ""
            self.last_user_file_key = file_exact or ""
            gen = stream_rag_chunks(
                request_message,
                folder_storage_key=folder_key,
                file_key_exact=file_exact,
                chat_mode=mode,
            )
            accumulated = ""
            last_flush = time.monotonic()
            throttle_s = 0.055
            while True:
                if self.cancel_stream_requested:
                    reply = RagReply(
                        content=(accumulated.strip() or "Generation stopped."),
                        mode=mode,
                        sources=[],
                        error="",
                        retryable=False,
                    )
                    break
                kind, payload = await asyncio.to_thread(stream_iter_next, gen)
                if kind == "done":
                    reply = payload
                    break
                accumulated += payload
                self.streaming_text = accumulated
                now = time.monotonic()
                if now - last_flush >= throttle_s:
                    last_flush = now
                    yield
            yield
            self.streaming_text = ""
            sources_payload = [
                {
                    "source_index": src.source_index,
                    "file_key": src.file_key,
                    "source_name": src.source_name,
                    "chunk_index": src.chunk_index,
                    "score": src.score,
                }
                for src in reply.sources
            ]
            if response_replace_id:
                replaced = await update_assistant_message(
                    message_id=response_replace_id,
                    user_id=auth.user_id,
                    content=reply.content,
                    sources=sources_payload,
                )
                assistant_message_id = response_replace_id if replaced else ""
            else:
                assistant_message_id = ""
            if not assistant_message_id:
                assistant_message_id = await append_assistant_message(
                    self.active_conversation_id,
                    user_id=auth.user_id,
                    content=reply.content,
                    sources=sources_payload,
                )
            if len(self.messages) <= 2:
                await rename_conversation(self.active_conversation_id, user_id=auth.user_id, title=clipped[:80])
                self.sidebar_threads = await list_chat_payload(auth.user_id)
            was_cancelled = self.cancel_stream_requested
            self._push_assistant_message(
                reply,
                message_id=assistant_message_id,
                stopped_by_user=was_cancelled,
                replace_index=response_replace_index if assistant_message_id == response_replace_id else -1,
            )
            if reply.error and reply.retryable and not was_cancelled:
                self.last_failed_prompt = request_message
                self.last_failed_mode = mode
                self.last_failed_folder_key = folder_key or ""
                self.last_failed_file_key = file_exact or ""
                self.last_failed_assistant_message_id = assistant_message_id
            else:
                self.last_failed_prompt = ""
                self.last_failed_mode = "normal"
                self.last_failed_folder_key = ""
                self.last_failed_file_key = ""
                self.last_failed_assistant_message_id = ""
            yield self.scroll_chat_to_latest()
        finally:
            self.rag_busy = False
            self.cancel_stream_requested = False
            self.streaming_text = ""
            self.chat_upload_previews = []
            self.chat_upload_error = ""
            self.show_chat_image_preview = False
            self.chat_preview_name = ""
            self.chat_preview_url = ""
            self.chat_preview_images = []
            self.chat_preview_index = 0
            self._stash_clear_chat_files()

    async def retry_last_turn(self):
        prompt = self.last_failed_prompt.strip()
        if not prompt or self.rag_busy:
            return
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            return
        self.rag_busy = True
        self.cancel_stream_requested = False
        self.streaming_text = ""
        mode = self.last_failed_mode if self.last_failed_mode in {"normal", "reasoning"} else "normal"
        self.streaming_mode = mode
        folder_key = self.last_failed_folder_key or None
        file_exact = self.last_failed_file_key or None
        target_assistant_id = (self.last_failed_assistant_message_id or "").strip()
        target_assistant_index = next(
            (i for i, row in enumerate(self.messages) if str(row.get("id", "")).strip() == target_assistant_id),
            -1,
        )
        self.chat_mode = mode
        try:
            yield
            gen = stream_rag_chunks(
                prompt,
                folder_storage_key=folder_key,
                file_key_exact=file_exact,
                chat_mode=mode,
            )
            accumulated = ""
            last_flush = time.monotonic()
            throttle_s = 0.055
            while True:
                if self.cancel_stream_requested:
                    reply = RagReply(
                        content=(accumulated.strip() or "Generation stopped."),
                        mode=mode,
                        sources=[],
                        error="",
                        retryable=False,
                    )
                    break
                kind, payload = await asyncio.to_thread(stream_iter_next, gen)
                if kind == "done":
                    reply = payload
                    break
                accumulated += payload
                self.streaming_text = accumulated
                now = time.monotonic()
                if now - last_flush >= throttle_s:
                    last_flush = now
                    yield
            yield
            self.streaming_text = ""
            sources_payload = [
                {
                    "source_index": src.source_index,
                    "file_key": src.file_key,
                    "source_name": src.source_name,
                    "chunk_index": src.chunk_index,
                    "score": src.score,
                }
                for src in reply.sources
            ]
            assistant_message_id = ""
            if target_assistant_id:
                replaced = await update_assistant_message(
                    message_id=target_assistant_id,
                    user_id=auth.user_id,
                    content=reply.content,
                    sources=sources_payload,
                )
                if replaced:
                    assistant_message_id = target_assistant_id
            if not assistant_message_id:
                assistant_message_id = await append_assistant_message(
                    self.active_conversation_id,
                    user_id=auth.user_id,
                    content=reply.content,
                    sources=sources_payload,
                )
            was_cancelled = self.cancel_stream_requested
            self._push_assistant_message(
                reply,
                message_id=assistant_message_id,
                stopped_by_user=was_cancelled,
                replace_index=target_assistant_index if assistant_message_id == target_assistant_id else -1,
            )
            if reply.error and reply.retryable and not was_cancelled:
                self.last_failed_prompt = prompt
                self.last_failed_assistant_message_id = assistant_message_id
            else:
                self.last_failed_prompt = ""
                self.last_failed_mode = "normal"
                self.last_failed_folder_key = ""
                self.last_failed_file_key = ""
                self.last_failed_assistant_message_id = ""
            yield self.scroll_chat_to_latest()
        finally:
            self.rag_busy = False
            self.cancel_stream_requested = False
            self.streaming_text = ""

    async def regenerate_last_response(self):
        prompt = self.last_user_prompt.strip()
        if not prompt or self.rag_busy:
            return
        self.rag_busy = True
        self.cancel_stream_requested = False
        self.streaming_text = ""
        mode = self.last_user_mode if self.last_user_mode in {"normal", "reasoning"} else "normal"
        self.streaming_mode = mode
        folder_key = self.last_user_folder_key or None
        file_exact = self.last_user_file_key or None
        self.chat_mode = mode
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            self.rag_busy = False
            self.streaming_text = ""
            return
        try:
            yield
            gen = stream_rag_chunks(
                prompt,
                folder_storage_key=folder_key,
                file_key_exact=file_exact,
                chat_mode=mode,
            )
            accumulated = ""
            last_flush = time.monotonic()
            throttle_s = 0.055
            while True:
                if self.cancel_stream_requested:
                    reply = RagReply(
                        content=(accumulated.strip() or "Generation stopped."),
                        mode=mode,
                        sources=[],
                        error="",
                        retryable=False,
                    )
                    break
                kind, payload = await asyncio.to_thread(stream_iter_next, gen)
                if kind == "done":
                    reply = payload
                    break
                accumulated += payload
                self.streaming_text = accumulated
                now = time.monotonic()
                if now - last_flush >= throttle_s:
                    last_flush = now
                    yield
            yield
            self.streaming_text = ""
            assistant_message_id = await append_assistant_message(
                self.active_conversation_id,
                user_id=auth.user_id,
                content=reply.content,
                sources=[
                    {
                        "source_index": src.source_index,
                        "file_key": src.file_key,
                        "source_name": src.source_name,
                        "chunk_index": src.chunk_index,
                        "score": src.score,
                    }
                    for src in reply.sources
                ],
            )
            self._push_assistant_message(
                reply,
                message_id=assistant_message_id,
                stopped_by_user=self.cancel_stream_requested,
            )
            yield self.scroll_chat_to_latest()
        finally:
            self.rag_busy = False
            self.cancel_stream_requested = False
            self.streaming_text = ""

    def open_new_chat_confirm(self) -> None:
        self.show_new_chat_confirm = True

    def cancel_new_chat_confirm(self) -> None:
        self.show_new_chat_confirm = False

    def confirm_new_chat(self) -> None:
        self.show_new_chat_confirm = False
        self.messages = []
        self.message_feedback = {}
        self.draft_message = ""
        self.streaming_text = ""
        self.active_conversation_id = ""
        self.suggested_prompts = build_hybrid_suggestions(folder_name="", file_name="")

    def new_chat(self) -> None:
        """Clear thread without confirmation (internal / legacy)."""
        self.messages = []
        self.message_feedback = {}
        self.draft_message = ""
        self.streaming_text = ""

    def set_chat_sidebar_width_pct(self, value: int) -> None:
        self.chat_sidebar_width_pct = max(15, min(48, int(value)))

    def commit_chat_sidebar_width_from_drag(self, value: Any) -> None:
        try:
            n = int(round(float(value)))
        except (TypeError, ValueError):
            n = int(self.chat_sidebar_width_pct)
        self.set_chat_sidebar_width_pct(n)

    def on_chat_divider_mouse_down(self):
        return rx.call_script(
            _CHAT_DIVIDER_DRAG_JS,
            callback=ChatState.commit_chat_sidebar_width_from_drag,
        )

    def show_chat_history_mobile(self) -> None:
        self.chat_mobile_view = "history"

    def show_chat_content_mobile(self) -> None:
        self.chat_mobile_view = "content"
