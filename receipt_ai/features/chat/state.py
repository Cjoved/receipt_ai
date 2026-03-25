import reflex as rx

from receipt_ai.features.chat.service import list_chat_payload


class ChatState(rx.State):
    """State container for chat feature."""

    history: list[str] = list_chat_payload()
    draft_message: str = ""

    def load_history(self) -> None:
        """Refresh chat history from service layer."""

        self.history = list_chat_payload()

    def set_draft(self, value: str) -> None:
        self.draft_message = value

    def send_draft(self) -> None:
        """Append current draft to chat history."""

        message = self.draft_message.strip()
        if not message:
            return
        self.history.append(message)
        self.draft_message = ""
