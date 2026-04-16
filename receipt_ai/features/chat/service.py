from datetime import UTC, datetime

from sqlalchemy import desc, select

from receipt_ai.core.db.models import Conversation, Message
from receipt_ai.core.db.session import get_session
from receipt_ai.features.chat.models import ConversationItem


def list_chat_history(user_id: str) -> list[ConversationItem]:
    with get_session() as db:
        rows = db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at), desc(Conversation.created_at))
        ).all()
        return [ConversationItem(id=row.id, title=row.title) for row in rows]


def list_chat_payload(user_id: str) -> list[dict[str, str]]:
    return [{"id": item.id, "title": item.title} for item in list_chat_history(user_id)]


def create_conversation(user_id: str, *, title: str) -> str:
    clean_title = title.strip() or "New chat"
    with get_session() as db:
        row = Conversation(user_id=user_id, title=clean_title)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def rename_conversation(conversation_id: str, *, title: str) -> None:
    clean_title = title.strip() or "New chat"
    with get_session() as db:
        row = db.scalar(select(Conversation).where(Conversation.id == conversation_id))
        if row is None:
            return
        row.title = clean_title
        row.updated_at = datetime.now(UTC)
        db.commit()


def append_message(conversation_id: str, *, role: str, content: str) -> None:
    with get_session() as db:
        msg = Message(conversation_id=conversation_id, role=role, content=content)
        db.add(msg)
        conv = db.scalar(select(Conversation).where(Conversation.id == conversation_id))
        if conv is not None:
            conv.updated_at = datetime.now(UTC)
        db.commit()


def list_conversation_messages(conversation_id: str) -> list[dict[str, str]]:
    with get_session() as db:
        rows = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        ).all()
        return [{"role": row.role, "content": row.content} for row in rows]
