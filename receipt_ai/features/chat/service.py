from datetime import UTC, datetime
import json
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import selectinload

from receipt_ai.core.db.models import Conversation, Message, MessageFeedback, MessageSource
from receipt_ai.core.db.session import get_async_session
from receipt_ai.features.chat.models import ConversationItem

_ATTACH_PREFIX = "[[ATTACHMENTS_JSON]]"
_ATTACH_SUFFIX = "[[/ATTACHMENTS_JSON]]"


def _sanitize_attachments(attachments: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    clean: list[dict[str, str]] = []
    for row in attachments or []:
        name = str(row.get("name", "")).strip()
        preview_url = str(row.get("preview_url", "")).strip()
        if not preview_url:
            continue
        clean.append({"name": name, "preview_url": preview_url})
    return clean


def _source_counts(sources: list[MessageSource]) -> tuple[int, int]:
    """Return (unique_file_count, chunk_count) for message sources."""
    chunk_count = len(sources)
    unique_files = {str(src.file_key).strip() for src in sources if str(src.file_key).strip()}
    return (len(unique_files), chunk_count)


def _pack_user_message(content: str, attachments: list[dict[str, Any]] | None) -> str:
    clean = _sanitize_attachments(attachments)
    if not clean:
        return content
    payload = json.dumps(clean, separators=(",", ":"), ensure_ascii=True)
    return f"{_ATTACH_PREFIX}{payload}{_ATTACH_SUFFIX}\n{content}"


def _unpack_user_message(content: str) -> tuple[str, list[dict[str, str]]]:
    raw = str(content or "")
    if not raw.startswith(_ATTACH_PREFIX):
        return (raw, [])
    end = raw.find(_ATTACH_SUFFIX)
    if end < 0:
        return (raw, [])
    payload = raw[len(_ATTACH_PREFIX) : end]
    body = raw[end + len(_ATTACH_SUFFIX) :].lstrip("\n")
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return (body or raw, [])
    if not isinstance(parsed, list):
        return (body or raw, [])
    return (body or raw, _sanitize_attachments(parsed))


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


async def rename_conversation(conversation_id: str, *, user_id: str, title: str) -> None:
    clean_title = title.strip() or "New chat"
    async with get_async_session() as db:
        row = await db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
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


async def append_message(
    conversation_id: str,
    *,
    user_id: str,
    role: str,
    content: str,
    attachments: list[dict[str, Any]] | None = None,
) -> str:
    async with get_async_session() as db:
        conv = await db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if conv is None:
            return ""
        stored_content = _pack_user_message(content, attachments) if role == "user" else content
        msg = Message(conversation_id=conversation_id, role=role, content=stored_content)
        db.add(msg)
        conv.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(msg)
        return str(msg.id)


async def append_assistant_message(
    conversation_id: str,
    *,
    user_id: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
) -> str:
    async with get_async_session() as db:
        conv = await db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if conv is None:
            return ""
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

        conv.updated_at = datetime.now(UTC)
        await db.commit()
        return str(msg.id)


async def list_conversation_messages(conversation_id: str, *, user_id: str) -> list[dict[str, Any]]:
    async with get_async_session() as db:
        owner = await db.scalar(
            select(Conversation.id).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        if owner is None:
            return []
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
            unique_file_count, chunk_count = _source_counts(sources)
            display_content, attachments = _unpack_user_message(row.content) if row.role == "user" else (row.content, [])
            first_attachment = attachments[0] if attachments else {}
            second_attachment = attachments[1] if len(attachments) > 1 else {}
            third_attachment = attachments[2] if len(attachments) > 2 else {}
            payload.append(
                {
                    "id": str(row.id),
                    "role": row.role,
                    "content": display_content,
                    "attachments": attachments,
                    "attachments_list": attachments,
                    "attachments_count": len(attachments),
                    "attachments_more_label": (f"+{len(attachments) - 1} more" if len(attachments) > 1 else ""),
                    "attachment_name_1": str(first_attachment.get("name", "")).strip(),
                    "attachment_preview_url_1": str(first_attachment.get("preview_url", "")).strip(),
                    "attachment_name_2": str(second_attachment.get("name", "")).strip(),
                    "attachment_preview_url_2": str(second_attachment.get("preview_url", "")).strip(),
                    "attachment_name_3": str(third_attachment.get("name", "")).strip(),
                    "attachment_preview_url_3": str(third_attachment.get("preview_url", "")).strip(),
                    "attachment_name": str(first_attachment.get("name", "")).strip(),
                    "attachment_preview_url": str(first_attachment.get("preview_url", "")).strip(),
                    "mode": "normal",
                    "is_error": "0",
                    "sources_count": len(sources),
                    "sources_file_count": unique_file_count,
                    "sources_chunk_count": chunk_count,
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


async def upsert_message_feedback(*, message_id: str, user_id: str, vote: str) -> bool:
    clean_vote = (vote or "").strip().lower()
    if clean_vote not in {"up", "down"}:
        return False
    try:
        async with get_async_session() as db:
            row = await db.scalar(
                select(MessageFeedback)
                .join(Message, Message.id == MessageFeedback.message_id)
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    MessageFeedback.message_id == message_id,
                    MessageFeedback.user_id == user_id,
                    Conversation.user_id == user_id,
                )
            )
            if row is None:
                owner = await db.scalar(
                    select(Message.id)
                    .join(Conversation, Conversation.id == Message.conversation_id)
                    .where(
                        Message.id == message_id,
                        Conversation.user_id == user_id,
                    )
                )
                if owner is None:
                    return False
                row = MessageFeedback(message_id=message_id, user_id=user_id, vote=clean_vote)
                db.add(row)
            else:
                row.vote = clean_vote
                row.updated_at = datetime.now(UTC)
            await db.commit()
            return True
    except ProgrammingError:
        # Backward-compatible fallback when migration hasn't been applied yet.
        return False


async def list_message_feedback_map(conversation_id: str, *, user_id: str) -> dict[str, str]:
    try:
        async with get_async_session() as db:
            rows = (
                await db.execute(
                    select(MessageFeedback.message_id, MessageFeedback.vote)
                    .join(Message, Message.id == MessageFeedback.message_id)
                    .join(Conversation, Conversation.id == Message.conversation_id)
                    .where(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id,
                        MessageFeedback.user_id == user_id,
                    )
                )
            ).all()
        return {str(message_id): str(vote) for (message_id, vote) in rows if str(vote) in {"up", "down"}}
    except ProgrammingError:
        # Backward-compatible fallback when migration hasn't been applied yet.
        return {}


async def list_message_sources_for_user(message_id: str, *, user_id: str) -> list[dict[str, Any]]:
    async with get_async_session() as db:
        owner = await db.scalar(
            select(Message.id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.id == message_id,
                Conversation.user_id == user_id,
            )
        )
        if owner is None:
            return []
        rows = (
            await db.scalars(
                select(MessageSource)
                .where(MessageSource.message_id == message_id)
                .order_by(MessageSource.source_index.asc(), MessageSource.id.asc())
            )
        ).all()
        return [
            {
                "source_index": int(row.source_index),
                "file_key": str(row.file_key),
                "source_name": str(row.source_name),
                "chunk_index": int(row.chunk_index),
                "score": float(row.score),
            }
            for row in rows
        ]


async def update_user_message_content(
    *,
    message_id: str,
    user_id: str,
    content: str,
    attachments: list[dict[str, Any]] | None = None,
) -> bool:
    async with get_async_session() as db:
        row = await db.scalar(
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.id == message_id,
                Message.role == "user",
                Conversation.user_id == user_id,
            )
        )
        if row is None:
            return False
        row.content = _pack_user_message(content, attachments)
        await db.commit()
        return True


async def update_assistant_message(
    *,
    message_id: str,
    user_id: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
) -> bool:
    async with get_async_session() as db:
        row = await db.scalar(
            select(Message)
            .options(selectinload(Message.sources))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.id == message_id,
                Message.role == "assistant",
                Conversation.user_id == user_id,
            )
        )
        if row is None:
            return False
        row.content = content
        for src in list(row.sources):
            await db.delete(src)
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
                    message_id=row.id,
                    source_index=source_index,
                    file_key=file_key,
                    source_name=source_name,
                    chunk_index=chunk_index,
                    score=score,
                )
            )
        await db.commit()
        return True
