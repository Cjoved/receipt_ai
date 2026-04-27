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

    def test_latest_question_reorders_context_by_screenshot_timestamp(self):
        """Same-day screenshots: later HHMMSS in filename should appear as Source 1."""
        cfg = ExtractionConfig(
            deepseek_api_key="k",
            deepseek_base_url="https://api.deepseek.com",
            deepseek_chat_model="deepseek-chat",
            deepseek_reasoning_model="deepseek-reasoner",
            deepseek_timeout_seconds=30,
            rag_top_k=4,
        )
        hits = [
            RetrievedChunk(
                file_key="f/Screenshot 2026-04-20 160346.png",
                source_name="Screenshot 2026-04-20 160346.png",
                chunk_index=0,
                content="older chunk",
                score=0.99,
                section_type="text",
                uploaded_epoch=100,
            ),
            RetrievedChunk(
                file_key="f/Screenshot 2026-04-20 160351.png",
                source_name="Screenshot 2026-04-20 160351.png",
                chunk_index=0,
                content="newer chunk",
                score=0.5,
                section_type="text",
                uploaded_epoch=100,
            ),
        ]

        with (
            patch("receipt_ai.features.chat.rag_service.ChunkRetriever") as retriever_cls,
            patch("receipt_ai.features.chat.rag_service.OpenAI") as openai_cls,
        ):
            retriever_cls.return_value.retrieve.return_value = hits
            openai_cls.return_value.chat.completions.create.return_value.choices = [
                type("Choice", (), {"message": type("Msg", (), {"content": "ok"})()})()
            ]

            run_rag_reply("Summarize my latest receipt.", chat_mode="normal", config=cfg)

            messages = openai_cls.return_value.chat.completions.create.call_args.kwargs["messages"]
            human = next(m["content"] for m in messages if m["role"] == "user")
            self.assertIn("reordered for recency", human.lower())
            pos_newer = human.index("newer chunk")
            pos_older = human.index("older chunk")
            self.assertLess(pos_newer, pos_older)
            self.assertRegex(human, r"\[Source 1:.*160351")
            self.assertRegex(human, r"\[Source 2:.*160346")
            self.assertIn("implausible future ocr dates were ignored", human.lower())

    def test_latest_question_ignores_future_ocr_date_outlier(self):
        cfg = ExtractionConfig(
            deepseek_api_key="k",
            deepseek_base_url="https://api.deepseek.com",
            deepseek_chat_model="deepseek-chat",
            deepseek_reasoning_model="deepseek-reasoner",
            deepseek_timeout_seconds=30,
            rag_top_k=4,
        )
        hits = [
            RetrievedChunk(
                file_key="f/page_nov.txt",
                source_name="page_nov.txt",
                chunk_index=0,
                content="merchant: LJH FOODS\nDate: 11/19/26\ntotal: 595.64",
                score=0.99,
                section_type="text",
                uploaded_epoch=100,
            ),
            RetrievedChunk(
                file_key="f/page_apr.txt",
                source_name="page_apr.txt",
                chunk_index=1,
                content="merchant: PETRON\nDate: 04/07/2026\ntotal: 3,000.00",
                score=0.5,
                section_type="text",
                uploaded_epoch=100,
            ),
        ]
        with (
            patch("receipt_ai.features.chat.rag_service.ChunkRetriever") as retriever_cls,
            patch("receipt_ai.features.chat.rag_service.OpenAI") as openai_cls,
        ):
            retriever_cls.return_value.retrieve.return_value = hits
            openai_cls.return_value.chat.completions.create.return_value.choices = [
                type("Choice", (), {"message": type("Msg", (), {"content": "ok"})()})()
            ]
            run_rag_reply("latest receipt total and date", chat_mode="normal", config=cfg)
            messages = openai_cls.return_value.chat.completions.create.call_args.kwargs["messages"]
            human = next(m["content"] for m in messages if m["role"] == "user")
            pos_apr = human.index("page_apr")
            pos_nov = human.index("page_nov")
            self.assertLess(pos_apr, pos_nov)

    def test_retrieval_failure_returns_retryable_error(self):
        cfg = ExtractionConfig(deepseek_api_key="k")
        with patch("receipt_ai.features.chat.rag_service.ChunkRetriever") as retriever_cls:
            retriever_cls.return_value.retrieve.side_effect = RuntimeError("qdrant down")
            reply = run_rag_reply("hello", chat_mode="normal", config=cfg)
            self.assertEqual(reply.mode, "normal")
            self.assertTrue(reply.retryable)
            self.assertNotEqual(reply.error, "")
            self.assertIn("Retrieval failed", reply.content)

    def test_broad_mode_returns_deterministic_table_without_llm(self):
        cfg = ExtractionConfig(
            deepseek_api_key="",
            rag_enable_broad_aggregate_mode=True,
            rag_broad_top_k=40,
        )
        hits = [
            RetrievedChunk(
                file_key="folder/budget.pdf::p1",
                document_key="folder/budget.pdf",
                source_name="budget.pdf",
                chunk_index=0,
                content="merchant: PETRON\ndate: 04/07/2026\ntotal: Php3,000.00",
                score=0.8,
                section_type="pdf_page",
            ),
            RetrievedChunk(
                file_key="folder/budget.pdf::p2",
                document_key="folder/budget.pdf",
                source_name="budget.pdf",
                chunk_index=1,
                content="merchant: BON JOUR APPARTELLE\ntotal: ₱1,250.00",
                score=0.7,
                section_type="pdf_page",
            ),
        ]
        with (
            patch("receipt_ai.features.chat.rag_service.ChunkRetriever") as retriever_cls,
            patch("receipt_ai.features.chat.rag_service.OpenAI") as openai_cls,
        ):
            retriever_cls.return_value.retrieve.return_value = hits
            reply = run_rag_reply("Kunin mo lahat ng receipts at ilagay sa table.", config=cfg)

        self.assertIn("| Title | Amount | Source | Confidence |", reply.content)
        self.assertIn("Coverage summary", reply.content)
        self.assertIn("PETRON", reply.content)
        self.assertIn("BON JOUR APPARTELLE", reply.content)
        openai_cls.return_value.chat.completions.create.assert_not_called()

    def test_broad_mode_uses_broad_top_k_and_neighbor_flag(self):
        cfg = ExtractionConfig(
            deepseek_api_key="",
            rag_enable_broad_aggregate_mode=True,
            rag_enable_neighbor_expansion=True,
            rag_broad_top_k=55,
        )
        with patch("receipt_ai.features.chat.rag_service.ChunkRetriever") as retriever_cls:
            retriever_cls.return_value.retrieve.return_value = [
                RetrievedChunk(
                    file_key="f/a.pdf::p1",
                    document_key="f/a.pdf",
                    source_name="a.pdf",
                    chunk_index=0,
                    content="merchant: x\ntotal: 1.00",
                    score=1.0,
                    section_type="pdf_page",
                )
            ]
            run_rag_reply("all receipts table", config=cfg)
            kwargs = retriever_cls.return_value.retrieve.call_args.kwargs
            self.assertEqual(kwargs["top_k"], 55)
            self.assertTrue(kwargs["expand_neighbors"])

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
