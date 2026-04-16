import json
import tempfile
import unittest
from unittest.mock import patch

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.retrieval.chunk_json import (
    chunk_record_from_dict,
    load_chunks_from_file,
)
from receipt_ai.features.extraction.indexing.qdrant_index import build_qdrant_filter
from receipt_ai.features.extraction.retrieval.retriever import ChunkRetriever
from receipt_ai.features.extraction.retrieval.similarity import cosine_similarity, top_k_by_score


class QdrantFilterTests(unittest.TestCase):
    def test_build_filter_file_key(self):
        f = build_qdrant_filter(folder_prefix=None, file_key_exact="a/b.txt")
        assert f is not None
        self.assertEqual(len(f.must), 1)

    def test_build_filter_folder(self):
        f = build_qdrant_filter(folder_prefix="MyFolder", file_key_exact=None)
        assert f is not None

    def test_build_filter_global(self):
        self.assertIsNone(build_qdrant_filter(folder_prefix=None, file_key_exact=None))


class SimilarityTests(unittest.TestCase):
    def test_cosine_same_direction(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(a, b), 1.0, places=5)

    def test_cosine_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        self.assertAlmostEqual(cosine_similarity(a, b), 0.0, places=5)

    def test_top_k_order(self):
        scored = [(0.1, 0), (0.9, 1), (0.5, 2)]
        best = top_k_by_score(scored, 2)
        self.assertEqual(best[0][1], 1)
        self.assertEqual(best[1][1], 2)


class ChunkJsonTests(unittest.TestCase):
    def test_chunk_record_from_dict_roundtrip_fields(self):
        raw = {
            "file_key": "f/a.txt",
            "source_name": "a.txt",
            "chunk_index": 0,
            "content": "hello",
            "token_count_est": 1,
            "char_start": 0,
            "char_end": 5,
            "section_type": "text",
            "metadata": {"chunk_of": 1},
            "embedding": [0.0, 1.0, 0.0],
        }
        rec = chunk_record_from_dict(raw)
        assert rec is not None
        self.assertEqual(rec.file_key, "f/a.txt")
        self.assertEqual(rec.embedding, [0.0, 1.0, 0.0])

    def test_load_chunks_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = __import__("pathlib").Path(tmp) / "x.chunks.json"
            payload = [
                {
                    "file_key": "f/x.txt",
                    "source_name": "x.txt",
                    "chunk_index": 0,
                    "content": "z",
                    "token_count_est": 1,
                    "char_start": 0,
                    "char_end": 1,
                    "section_type": "text",
                    "metadata": {},
                    "embedding": [1.0, 0.0],
                }
            ]
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_chunks_from_file(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].content, "z")


class RetrieverTests(unittest.TestCase):
    def test_retrieve_respects_folder_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ExtractionConfig(index_output_dir=tmp, rag_top_k=4)
            sub = __import__("pathlib").Path(tmp) / "my_folder"
            sub.mkdir(parents=True)
            chunks_path = sub / "doc.txt.chunks.json"
            rows = [
                {
                    "file_key": "my_folder/doc.txt",
                    "source_name": "doc.txt",
                    "chunk_index": 0,
                    "content": "alpha beta",
                    "token_count_est": 2,
                    "char_start": 0,
                    "char_end": 10,
                    "section_type": "text",
                    "metadata": {},
                    "embedding": [1.0, 0.0],
                },
                {
                    "file_key": "other/doc.txt",
                    "source_name": "doc.txt",
                    "chunk_index": 0,
                    "content": "gamma",
                    "token_count_est": 1,
                    "char_start": 0,
                    "char_end": 5,
                    "section_type": "text",
                    "metadata": {},
                    "embedding": [0.0, 1.0],
                },
            ]
            chunks_path.write_text(json.dumps(rows), encoding="utf-8")

            with patch("receipt_ai.features.extraction.retrieval.retriever.FastEmbedProvider") as fe_cls:
                fe_cls.return_value.embed_query.return_value = [1.0, 0.0]
                r = ChunkRetriever(cfg)
                hits = r.retrieve("q", folder_prefix="my_folder")
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0].file_key, "my_folder/doc.txt")

    def test_retrieve_file_key_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ExtractionConfig(index_output_dir=tmp)
            p = __import__("pathlib").Path(tmp) / "f"
            p.mkdir()
            fp = p / "a.chunks.json"
            fp.write_text(
                json.dumps(
                    [
                        {
                            "file_key": "folder/a.txt",
                            "source_name": "a.txt",
                            "chunk_index": 0,
                            "content": "x",
                            "token_count_est": 1,
                            "char_start": 0,
                            "char_end": 1,
                            "section_type": "text",
                            "metadata": {},
                            "embedding": [1.0, 0.0],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            with patch("receipt_ai.features.extraction.retrieval.retriever.FastEmbedProvider") as fe_cls:
                fe_cls.return_value.embed_query.return_value = [1.0, 0.0]
                r = ChunkRetriever(cfg)
                hits = r.retrieve("q", file_key_exact="folder/a.txt")
                self.assertEqual(len(hits), 1)


if __name__ == "__main__":
    unittest.main()
