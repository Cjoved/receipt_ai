import asyncio
import time
import reflex as rx
from typing import Any

from receipt_ai.features.auth.state import AuthState
from receipt_ai.features.chat.rag_service import RagReply, stream_iter_next, stream_rag_chunks
from receipt_ai.features.chat.service import (
    append_assistant_message,
    append_message,
    create_conversation,
    delete_conversation,
    list_chat_payload,
    list_conversation_messages,
    rename_conversation,
)
from receipt_ai.features.files.state import FilesState

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

    @rx.var
    def chat_sidebar_width_css(self) -> str:
        return f"{self.chat_sidebar_width_pct}%"

    @rx.var
    def has_messages(self) -> bool:
        return len(self.messages) > 0

    @rx.var
    def can_send(self) -> bool:
        return (self.draft_message or "").strip() != "" and not self.rag_busy

    @rx.var
    def thinking_enabled(self) -> bool:
        return self.chat_mode == "reasoning"

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

    async def load_history(self) -> None:
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            self.sidebar_threads = []
            self.active_conversation_id = ""
            self.messages = []
            self.streaming_text = ""
            return
        self.sidebar_threads = await list_chat_payload(auth.user_id)
        if not self.sidebar_threads:
            self.active_conversation_id = ""
            self.messages = []
            self.streaming_text = ""
            return
        if not self.active_conversation_id:
            self.active_conversation_id = str(self.sidebar_threads[0].get("id", ""))
        self.streaming_text = ""
        await self._load_active_conversation_messages()

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
            self.streaming_text = ""
            return
        self.messages = await list_conversation_messages(convo_id)
        self.streaming_text = ""

    def set_draft(self, value: str) -> None:
        self.draft_message = value

    def set_chat_mode(self, value: str) -> None:
        mode = (value or "").strip().lower()
        if mode in {"normal", "reasoning"}:
            self.chat_mode = mode

    def toggle_thinking_mode(self) -> None:
        self.chat_mode = "normal" if self.chat_mode == "reasoning" else "reasoning"

    def _push_assistant_message(self, reply: RagReply) -> None:
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
        self.messages = [
            *self.messages,
            {
                "role": "assistant",
                "content": reply.content,
                "mode": reply.mode,
                "is_error": "1" if reply.error else "0",
                "sources": sources_payload,
                "sources_count": len(sources_payload),
                "sources_preview": ", ".join(
                    [f"Source {src['source_index']}: {src['source_name']}" for src in sources_payload[:2]]
                ),
            },
        ]

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
        if not message or self.rag_busy:
            return
        clipped = message[:2000]
        self.rag_busy = True
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

        if not self.active_conversation_id:
            self.active_conversation_id = await create_conversation(auth.user_id, title=clipped[:80])
            self.sidebar_threads = await list_chat_payload(auth.user_id)

        await append_message(self.active_conversation_id, role="user", content=clipped)
        self.messages = [
            *self.messages,
            {"role": "user", "content": clipped, "sources": [], "sources_count": 0, "sources_preview": ""},
        ]
        self.draft_message = ""
        try:
            yield
            files = await self.get_state(FilesState)
            folder_key = None
            file_exact = None
            if files.expanded_folder_name:
                folder_key = files._resolve_storage_folder_name(files.expanded_folder_name)
                if files.selected_child_file_name:
                    file_exact = f"{folder_key}/{files.selected_child_file_name}"
            mode = self.chat_mode
            gen = stream_rag_chunks(
                clipped,
                folder_storage_key=folder_key,
                file_key_exact=file_exact,
                chat_mode=mode,
            )
            accumulated = ""
            last_flush = time.monotonic()
            throttle_s = 0.055
            while True:
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
            await append_assistant_message(
                self.active_conversation_id,
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
            if len(self.messages) <= 2:
                await rename_conversation(self.active_conversation_id, title=clipped[:80])
                self.sidebar_threads = await list_chat_payload(auth.user_id)
            self._push_assistant_message(reply)
            if reply.error and reply.retryable:
                self.last_failed_prompt = clipped
                self.last_failed_mode = mode
                self.last_failed_folder_key = folder_key or ""
                self.last_failed_file_key = file_exact or ""
            else:
                self.last_failed_prompt = ""
                self.last_failed_mode = "normal"
                self.last_failed_folder_key = ""
                self.last_failed_file_key = ""
            yield self.scroll_chat_to_latest()
        finally:
            self.rag_busy = False
            self.streaming_text = ""

    async def retry_last_turn(self):
        prompt = self.last_failed_prompt.strip()
        if not prompt or self.rag_busy:
            return
        self.rag_busy = True
        self.streaming_text = ""
        mode = self.last_failed_mode if self.last_failed_mode in {"normal", "reasoning"} else "normal"
        self.streaming_mode = mode
        folder_key = self.last_failed_folder_key or None
        file_exact = self.last_failed_file_key or None
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
            await append_assistant_message(
                self.active_conversation_id,
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
            self._push_assistant_message(reply)
            if reply.error and reply.retryable:
                self.last_failed_prompt = prompt
            else:
                self.last_failed_prompt = ""
                self.last_failed_mode = "normal"
                self.last_failed_folder_key = ""
                self.last_failed_file_key = ""
            yield self.scroll_chat_to_latest()
        finally:
            self.rag_busy = False
            self.streaming_text = ""

    def open_new_chat_confirm(self) -> None:
        self.show_new_chat_confirm = True

    def cancel_new_chat_confirm(self) -> None:
        self.show_new_chat_confirm = False

    def confirm_new_chat(self) -> None:
        self.show_new_chat_confirm = False
        self.messages = []
        self.draft_message = ""
        self.streaming_text = ""
        self.active_conversation_id = ""

    def new_chat(self) -> None:
        """Clear thread without confirmation (internal / legacy)."""
        self.messages = []
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
