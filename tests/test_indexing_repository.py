import tempfile
import unittest

from receipt_ai.features.extraction.chunking.models import ChunkRecord
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.indexing.chunk_repository import ChunkRepository


class IndexingRepositoryTests(unittest.TestCase):
    def test_status_transitions_and_chunk_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ExtractionConfig(index_output_dir=tmp)
            repo = ChunkRepository(config)
            file_key = "My Files/receipt.csv"

            repo.set_status(file_key, "processing")
            self.assertEqual(repo.get_status(file_key), "processing")

            out = repo.save_chunks(
                "My Files",
                "receipt.csv",
                [
                    ChunkRecord(
                        file_key=file_key,
                        source_name="receipt.csv",
                        chunk_index=0,
                        content="hello world",
                        token_count_est=2,
                        char_start=0,
                        char_end=11,
                        section_type="table",
                        metadata={"chunk_of": 1},
                        embedding=[0.1, 0.2],
                    )
                ],
            )
            self.assertTrue(out.endswith(".chunks.json"))

            repo.set_status(file_key, "completed")
            self.assertEqual(repo.get_status(file_key), "completed")


if __name__ == "__main__":
    unittest.main()
