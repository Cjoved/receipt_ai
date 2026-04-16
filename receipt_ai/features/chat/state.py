import asyncio
import reflex as rx
from typing import Any

from receipt_ai.features.auth.state import AuthState
from receipt_ai.features.chat.rag_service import run_rag_reply
from receipt_ai.features.chat.service import (
    append_message,
    create_conversation,
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
    messages: list[dict[str, str]] = []
    draft_message: str = ""
    rag_busy: bool = False

    chat_sidebar_width_pct: int = 22
    chat_mobile_view: str = "history"
    show_new_chat_confirm: bool = False

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
            return
        self.sidebar_threads = list_chat_payload(auth.user_id)
        if not self.sidebar_threads:
            self.active_conversation_id = ""
            self.messages = []
            return
        if not self.active_conversation_id:
            self.active_conversation_id = str(self.sidebar_threads[0].get("id", ""))
        await self._load_active_conversation_messages()

    async def select_conversation(self, conversation_id: str) -> None:
        self.active_conversation_id = conversation_id
        await self._load_active_conversation_messages()

    async def _load_active_conversation_messages(self) -> None:
        convo_id = (self.active_conversation_id or "").strip()
        if not convo_id:
            self.messages = []
            return
        self.messages = list_conversation_messages(convo_id)

    def set_draft(self, value: str) -> None:
        self.draft_message = value

    async def send_draft(self) -> None:
        message = self.draft_message.strip()
        if not message or self.rag_busy:
            return
        clipped = message[:2000]
        self.rag_busy = True
        auth = await self.get_state(AuthState)
        if not auth.user_id:
            self.rag_busy = False
            self.messages = [
                *self.messages,
                {"role": "assistant", "content": "Please sign in first."},
            ]
            return

        if not self.active_conversation_id:
            self.active_conversation_id = create_conversation(auth.user_id, title=clipped[:80])
            self.sidebar_threads = list_chat_payload(auth.user_id)

        append_message(self.active_conversation_id, role="user", content=clipped)
        self.messages = [
            *self.messages,
            {"role": "user", "content": clipped},
        ]
        self.draft_message = ""
        try:
            files = await self.get_state(FilesState)
            folder_key = None
            file_exact = None
            if files.expanded_folder_name:
                folder_key = files._resolve_storage_folder_name(files.expanded_folder_name)
                if files.selected_child_file_name:
                    file_exact = f"{folder_key}/{files.selected_child_file_name}"
            reply = await asyncio.to_thread(
                run_rag_reply,
                clipped,
                folder_storage_key=folder_key,
                file_key_exact=file_exact,
            )
            append_message(self.active_conversation_id, role="assistant", content=reply)
            if len(self.messages) <= 2:
                rename_conversation(self.active_conversation_id, title=clipped[:80])
                self.sidebar_threads = list_chat_payload(auth.user_id)
            self.messages = [
                *self.messages,
                {"role": "assistant", "content": reply},
            ]
        finally:
            self.rag_busy = False

    def open_new_chat_confirm(self) -> None:
        self.show_new_chat_confirm = True

    def cancel_new_chat_confirm(self) -> None:
        self.show_new_chat_confirm = False

    def confirm_new_chat(self) -> None:
        self.show_new_chat_confirm = False
        self.messages = []
        self.draft_message = ""
        self.active_conversation_id = ""

    def new_chat(self) -> None:
        """Clear thread without confirmation (internal / legacy)."""
        self.messages = []
        self.draft_message = ""

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
