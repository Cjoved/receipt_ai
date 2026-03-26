from receipt_ai.features.chat.models import ChatItem


_SEED_CHATS: tuple[ChatItem, ...] = (
    ChatItem("Give me summary of attendance"),
    ChatItem("What is the URL for BANCNET?"),
    ChatItem("Give me a summary in table"),
    ChatItem("What phone mentioned in Sovereign file?"),
)


def list_chat_history() -> list[ChatItem]:
    """Return chat history list.

    In production this should read from conversation storage.
    """

    # Return a copy so callers don't mutate seed data directly.
    return list(_SEED_CHATS)


def list_chat_payload() -> list[str]:
    """Serialize chat entries to UI-friendly payload."""

    # Flatten dataclass records to plain strings for component rendering.
    return [item.text for item in list_chat_history()]
