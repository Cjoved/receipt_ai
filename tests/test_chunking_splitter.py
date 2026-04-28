import unittest

from receipt_ai.features.extraction.chunking.models import TextSegment
from receipt_ai.features.extraction.chunking.splitter import ChunkBuildInput, build_chunks
from receipt_ai.features.extraction.config import ExtractionConfig


class ChunkingSplitterTests(unittest.TestCase):
    def test_image_doc_type_forces_single_chunk(self):
        config = ExtractionConfig(chunk_size=20, chunk_overlap=0, chunk_min_chars=1)
        payload = ChunkBuildInput(
            file_key="My Files/receipt-image.png",
            source_name="receipt-image.png",
            doc_type="image",
            segments=[
                TextSegment(section_type="ocr", content="Item one 100 pesos"),
                TextSegment(section_type="ocr", content="Item two 200 pesos"),
            ],
        )

        chunks = build_chunks(payload, config)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[0].metadata.get("chunk_of"), 1)
        self.assertIn("Item one 100 pesos", chunks[0].content)
        self.assertIn("Item two 200 pesos", chunks[0].content)

    def test_non_image_doc_type_can_produce_multiple_chunks(self):
        config = ExtractionConfig(chunk_size=20, chunk_overlap=0, chunk_min_chars=1)
        payload = ChunkBuildInput(
            file_key="My Files/receipt.pdf",
            source_name="receipt.pdf",
            doc_type="pdf",
            segments=[
                TextSegment(
                    section_type="paragraph",
                    content="Alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima",
                )
            ],
        )

        chunks = build_chunks(payload, config)
        self.assertGreater(len(chunks), 1)


if __name__ == "__main__":
    unittest.main()
