import inspect
import unittest
from unittest.mock import MagicMock, patch

from receipt_ai.features.chat.rag_service import RagReply, run_rag_reply, stream_iter_next, stream_rag_chunks
from receipt_ai.features.chat.state import ChatState
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.retrieval.retriever import RetrievedChunk


class RagServiceTests(unittest.TestCase):
    def test_reasoning_mode_uses_reasoning_model_and_sources(self):
        cfg = ExtractionConfig(
            deepseek_api_key="k",
            deepseek_base_url="https://api.deepseek.com",
            deepseek_chat_model="deepseek-chat",
            deepseek_reasoning_model="deepseek-reasoner",
            deepseek_timeout_seconds=30,
            rag_top_k=3,
        )
        hits = [
            RetrievedChunk(
                file_key="Testing Files/a.pdf",
                source_name="a.pdf",
                chunk_index=2,
                content="sample chunk",
                score=0.91,
                section_type="text",
            )
        ]

        with (
            patch("receipt_ai.features.chat.rag_service.ChunkRetriever") as retriever_cls,
            patch("receipt_ai.features.chat.rag_service.OpenAI") as openai_cls,
        ):
            retriever_cls.return_value.retrieve.return_value = hits
            openai_cls.return_value.chat.completions.create.return_value.choices = [
                type("Choice", (), {"message": type("Msg", (), {"content": "Answer from reasoning."})()})()
            ]

            reply = run_rag_reply("What is this receipt?", chat_mode="reasoning", config=cfg)

            self.assertIsInstance(reply, RagReply)
            self.assertEqual(reply.mode, "reasoning")
            self.assertEqual(reply.content, "Answer from reasoning.")
            self.assertEqual(len(reply.sources), 1)
            self.assertEqual(reply.sources[0].source_name, "a.pdf")

            call_kwargs = openai_cls.return_value.chat.completions.create.call_args.kwargs
            self.assertEqual(call_kwargs["model"], "deepseek-reasoner")

    def test_retrieval_failure_returns_retryable_error(self):
        cfg = ExtractionConfig(deepseek_api_key="k")
        with patch("receipt_ai.features.chat.rag_service.ChunkRetriever") as retriever_cls:
            retriever_cls.return_value.retrieve.side_effect = RuntimeError("qdrant down")
            reply = run_rag_reply("hello", chat_mode="normal", config=cfg)
            self.assertEqual(reply.mode, "normal")
            self.assertTrue(reply.retryable)
            self.assertNotEqual(reply.error, "")
            self.assertIn("Retrieval failed", reply.content)

    def test_stream_rag_chunks_yields_deltas_and_final_reply(self):
        cfg = ExtractionConfig(
            deepseek_api_key="k",
            deepseek_base_url="https://api.deepseek.com",
            deepseek_chat_model="deepseek-chat",
            deepseek_reasoning_model="deepseek-reasoner",
            deepseek_timeout_seconds=30,
            rag_top_k=3,
        )
        hits = [
            RetrievedChunk(
                file_key="Testing Files/a.pdf",
                source_name="a.pdf",
                chunk_index=2,
                content="sample chunk",
                score=0.91,
                section_type="text",
            )
        ]

        def _chunk(text: str) -> MagicMock:
            delta = MagicMock()
            delta.content = text
            choice = MagicMock()
            choice.delta = delta
            ch = MagicMock()
            ch.choices = [choice]
            return ch

        stream_events = [_chunk("Hello "), _chunk("world.")]

        with (
            patch("receipt_ai.features.chat.rag_service.ChunkRetriever") as retriever_cls,
            patch("receipt_ai.features.chat.rag_service.OpenAI") as openai_cls,
        ):
            retriever_cls.return_value.retrieve.return_value = hits
            openai_cls.return_value.chat.completions.create.return_value = iter(stream_events)

            gen = stream_rag_chunks("What is this receipt?", chat_mode="normal", config=cfg)
            deltas: list[str] = []
            while True:
                kind, payload = stream_iter_next(gen)
                if kind == "done":
                    reply = payload
                    break
                deltas.append(payload)

            create_kw = openai_cls.return_value.chat.completions.create.call_args.kwargs
            self.assertTrue(create_kw.get("stream"))
            self.assertEqual(deltas, ["Hello ", "world."])
            self.assertIsInstance(reply, RagReply)
            self.assertEqual(reply.content, "Hello world.")
            self.assertEqual(len(reply.sources), 1)

    def test_stream_rag_chunks_no_key_returns_only_final_reply(self):
        cfg = ExtractionConfig(deepseek_api_key="")
        gen = stream_rag_chunks("hello", chat_mode="normal", config=cfg)
        kind, payload = stream_iter_next(gen)
        self.assertEqual(kind, "done")
        self.assertIsInstance(payload, RagReply)
        self.assertIn("DeepSeek API key", payload.content)

    def test_send_draft_and_retry_are_async_generators(self):
        send = getattr(ChatState.send_draft, "fn", ChatState.send_draft)
        retry = getattr(ChatState.retry_last_turn, "fn", ChatState.retry_last_turn)
        self.assertTrue(inspect.isasyncgenfunction(send))
        self.assertTrue(inspect.isasyncgenfunction(retry))


if __name__ == "__main__":
    unittest.main()
