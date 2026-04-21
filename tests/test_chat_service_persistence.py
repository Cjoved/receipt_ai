import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from receipt_ai.core.db.base import Base
from receipt_ai.core.db.models import Conversation, Message, User
from receipt_ai.features.chat import service as chat_service


class ChatServicePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_local = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )

        self._orig_get_async_session = chat_service.get_async_session

        @asynccontextmanager
        async def _test_get_async_session():
            async with self.session_local() as session:
                yield session

        chat_service.get_async_session = _test_get_async_session

        async with self.session_local() as db:
            user = User(email="test@example.com", password_hash="x", display_name="Tester", is_active=True)
            db.add(user)
            await db.flush()
            self.user_id = user.id
            convo = Conversation(user_id=self.user_id, title="Test Thread", created_at=datetime.now(UTC))
            db.add(convo)
            await db.flush()
            self.conversation_id = convo.id
            await db.commit()

    async def asyncTearDown(self):
        chat_service.get_async_session = self._orig_get_async_session
        await self.engine.dispose()

    async def test_assistant_sources_persist_and_reload(self):
        await chat_service.append_message(self.conversation_id, role="user", content="question")
        await chat_service.append_assistant_message(
            self.conversation_id,
            content="answer",
            sources=[
                {
                    "source_index": 1,
                    "file_key": "Testing Files/a.pdf",
                    "source_name": "a.pdf",
                    "chunk_index": 3,
                    "score": 0.88,
                }
            ],
        )

        rows = await chat_service.list_conversation_messages(self.conversation_id)
        self.assertEqual(len(rows), 2)
        assistant = rows[-1]
        self.assertEqual(assistant["role"], "assistant")
        self.assertEqual(assistant["content"], "answer")
        self.assertEqual(len(assistant["sources"]), 1)
        self.assertEqual(assistant["sources"][0]["file_key"], "Testing Files/a.pdf")

    async def test_conversation_updated_at_changes_on_append(self):
        async with self.session_local() as db:
            before_row = await db.scalar(select(Conversation).where(Conversation.id == self.conversation_id))
            before = before_row.updated_at if before_row else None
        await chat_service.append_message(self.conversation_id, role="user", content="hello")
        async with self.session_local() as db:
            after_row = await db.scalar(select(Conversation).where(Conversation.id == self.conversation_id))
            after = after_row.updated_at if after_row else None
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        self.assertGreaterEqual(after, before)


if __name__ == "__main__":
    unittest.main()
