from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from receipt_ai.core.db.models import Conversation, Message, MessageSource
from receipt_ai.core.db.session import get_async_session
from receipt_ai.features.chat.models import ConversationItem


async def list_chat_history(user_id: str) -> list[ConversationItem]:
    async with get_async_session() as db:
        rows = (
            await db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at), desc(Conversation.created_at))
            )
        ).all()
        return [ConversationItem(id=row.id, title=row.title) for row in rows]


async def list_chat_payload(user_id: str) -> list[dict[str, str]]:
    return [{"id": item.id, "title": item.title} for item in await list_chat_history(user_id)]


async def create_conversation(user_id: str, *, title: str) -> str:
    clean_title = title.strip() or "New chat"
    async with get_async_session() as db:
        row = Conversation(user_id=user_id, title=clean_title)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row.id


async def rename_conversation(conversation_id: str, *, title: str) -> None:
    clean_title = title.strip() or "New chat"
    async with get_async_session() as db:
        row = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
        if row is None:
            return
        row.title = clean_title
        row.updated_at = datetime.now(UTC)
        await db.commit()


async def delete_conversation(conversation_id: str, *, user_id: str) -> None:
    """Delete a conversation owned by the given user."""
    async with get_async_session() as db:
        row = await db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if row is None:
            return
        await db.delete(row)
        await db.commit()


async def append_message(conversation_id: str, *, role: str, content: str) -> str:
    async with get_async_session() as db:
        msg = Message(conversation_id=conversation_id, role=role, content=content)
        db.add(msg)
        conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
        if conv is not None:
            conv.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(msg)
        return str(msg.id)


async def append_assistant_message(
    conversation_id: str,
    *,
    content: str,
    sources: list[dict[str, Any]] | None = None,
) -> str:
    async with get_async_session() as db:
        msg = Message(conversation_id=conversation_id, role="assistant", content=content)
        db.add(msg)
        await db.flush()

        for i, src in enumerate(sources or [], start=1):
            file_key = str(src.get("file_key", "")).strip()
            source_name = str(src.get("source_name", "")).strip() or file_key
            if not file_key:
                continue
            try:
                chunk_index = int(src.get("chunk_index", 0))
            except (TypeError, ValueError):
                chunk_index = 0
            try:
                score = float(src.get("score", 0.0))
            except (TypeError, ValueError):
                score = 0.0
            source_index = int(src.get("source_index", i) or i)
            db.add(
                MessageSource(
                    message_id=msg.id,
                    source_index=source_index,
                    file_key=file_key,
                    source_name=source_name,
                    chunk_index=chunk_index,
                    score=score,
                )
            )

        conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
        if conv is not None:
            conv.updated_at = datetime.now(UTC)
        await db.commit()
        return str(msg.id)


async def list_conversation_messages(conversation_id: str) -> list[dict[str, Any]]:
    async with get_async_session() as db:
        rows = (
            await db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(selectinload(Message.sources))
            .order_by(Message.created_at.asc())
            )
        ).all()
        payload: list[dict[str, Any]] = []
        for row in rows:
            sources = sorted(list(row.sources), key=lambda s: int(s.source_index))
            payload.append(
                {
                    "id": str(row.id),
                    "role": row.role,
                    "content": row.content,
                    "mode": "normal",
                    "is_error": "0",
                    "sources_count": len(sources),
                    "sources_preview": ", ".join(
                        [f"Source {int(src.source_index)}: {src.source_name}" for src in sources[:2]]
                    ),
                    "sources": [
                        {
                            "source_index": int(src.source_index),
                            "file_key": src.file_key,
                            "source_name": src.source_name,
                            "chunk_index": int(src.chunk_index),
                            "score": float(src.score),
                        }
                        for src in sources
                    ],
                }
            )
        return payload
