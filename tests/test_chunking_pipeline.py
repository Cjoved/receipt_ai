import unittest

from receipt_ai.features.extraction.chunking import (
    ChunkBuildInput,
    build_chunks,
    normalize_extracted_text,
    segment_text_for_chunking,
)
from receipt_ai.features.extraction.config import ExtractionConfig


class ChunkingPipelineTests(unittest.TestCase):
    def test_normalize_text_keeps_paragraph_shape(self):
        raw = "HelloWorld123\n\n\nLine\x01 with\tspaces"
        normalized = normalize_extracted_text(raw)
        self.assertIn("Hello World 123", normalized)
        self.assertIn("\n\n", normalized)

    def test_segment_csv_detects_table_segments(self):
        text = "a,b,c\n1,2,3\n4,5,6"
        segments = segment_text_for_chunking(text, "sheet.csv")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].section_type, "table")

    def test_build_chunks_adds_metadata_and_indices(self):
        config = ExtractionConfig(chunk_size=80, chunk_overlap=10, chunk_min_chars=10)
        segments = segment_text_for_chunking(
            "Para one.\n\nPara two with enough length to split and keep chunk metadata.",
            "note.txt",
        )
        chunks = build_chunks(
            ChunkBuildInput(
                file_key="folder/note.txt",
                source_name="note.txt",
                doc_type="txt",
                segments=segments,
            ),
            config,
        )
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertIn("chunk_of", chunks[0].metadata)


if __name__ == "__main__":
    unittest.main()
