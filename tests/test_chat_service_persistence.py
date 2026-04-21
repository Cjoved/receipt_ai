import unittest
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from receipt_ai.core.db.base import Base
from receipt_ai.core.db.models import Conversation, Message, User
from receipt_ai.features.chat import service as chat_service


class ChatServicePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, class_=Session)

        self._orig_get_session = chat_service.get_session
        chat_service.get_session = self.session_local

        with self.session_local() as db:
            user = User(email="test@example.com", password_hash="x", display_name="Tester", is_active=True)
            db.add(user)
            db.flush()
            self.user_id = user.id
            convo = Conversation(user_id=self.user_id, title="Test Thread", created_at=datetime.now(UTC))
            db.add(convo)
            db.flush()
            self.conversation_id = convo.id
            db.commit()

    def tearDown(self):
        chat_service.get_session = self._orig_get_session
        self.engine.dispose()

    def test_assistant_sources_persist_and_reload(self):
        chat_service.append_message(self.conversation_id, role="user", content="question")
        chat_service.append_assistant_message(
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

        rows = chat_service.list_conversation_messages(self.conversation_id)
        self.assertEqual(len(rows), 2)
        assistant = rows[-1]
        self.assertEqual(assistant["role"], "assistant")
        self.assertEqual(assistant["content"], "answer")
        self.assertEqual(len(assistant["sources"]), 1)
        self.assertEqual(assistant["sources"][0]["file_key"], "Testing Files/a.pdf")

    def test_conversation_updated_at_changes_on_append(self):
        with self.session_local() as db:
            before = db.get(Conversation, self.conversation_id).updated_at
        chat_service.append_message(self.conversation_id, role="user", content="hello")
        with self.session_local() as db:
            after = db.get(Conversation, self.conversation_id).updated_at
        self.assertGreaterEqual(after, before)


if __name__ == "__main__":
    unittest.main()
