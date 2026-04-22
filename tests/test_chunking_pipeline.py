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

    def test_pdf_segments_keep_page_indices_in_chunk_metadata(self):
        config = ExtractionConfig(chunk_size=300, chunk_overlap=20, chunk_min_chars=5)
        text = (
            "--- Page 1 ---\n"
            "Merchant A\nTotal 100\n\n"
            "--- Page 2 ---\n"
            "Merchant A continued\nTax 12\n"
        )
        segments = segment_text_for_chunking(text, "receipt.pdf")
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].page_index, 1)
        self.assertEqual(segments[1].page_index, 2)

        chunks = build_chunks(
            ChunkBuildInput(
                file_key="Folder/receipt.pdf",
                source_name="receipt.pdf",
                doc_type="pdf",
                segments=segments,
            ),
            config,
        )
        self.assertGreaterEqual(len(chunks), 2)
        page_values = {ch.metadata.get("page_index") for ch in chunks}
        self.assertIn(1, page_values)
        self.assertIn(2, page_values)
        self.assertTrue(all(ch.metadata.get("file_type") == "pdf" for ch in chunks))
        self.assertTrue(all(isinstance(ch.metadata.get("uploaded_epoch"), int) for ch in chunks))
        self.assertTrue(any("::p1" in ch.file_key for ch in chunks))
        self.assertTrue(any("::p2" in ch.file_key for ch in chunks))


if __name__ == "__main__":
    unittest.main()
