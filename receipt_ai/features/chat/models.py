from dataclasses import dataclass


@dataclass(frozen=True)
class ChatItem:
    """Domain model for chat history entries."""

    text: str
