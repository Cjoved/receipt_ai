import tempfile
import time
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

    def test_begin_processing_blocks_active_lock_and_recovers_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ExtractionConfig(index_output_dir=tmp)
            repo = ChunkRepository(config)
            file_key = "My Files/receipt.csv"

            claimed_first, recovered_first = repo.begin_processing(file_key, stale_after_seconds=120)
            self.assertTrue(claimed_first)
            self.assertFalse(recovered_first)

            claimed_second, recovered_second = repo.begin_processing(file_key, stale_after_seconds=120)
            self.assertFalse(claimed_second)
            self.assertFalse(recovered_second)

            state = repo._load_statuses()
            state[file_key.casefold()]["processing_started_epoch"] = int(time.time()) - 1000
            repo._write_statuses(state)

            claimed_third, recovered_third = repo.begin_processing(file_key, stale_after_seconds=60)
            self.assertTrue(claimed_third)
            self.assertTrue(recovered_third)
            self.assertEqual(repo.get_status(file_key), "processing")

    def test_begin_processing_recovers_legacy_processing_without_started_epoch(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ExtractionConfig(index_output_dir=tmp)
            repo = ChunkRepository(config)
            file_key = "Testing Files/Official Receipt from April 18 - 22.pdf"
            state = {
                file_key: {
                    "status": "processing",
                    "reason": "",
                }
            }
            repo._write_statuses(state)

            claimed, recovered = repo.begin_processing(file_key, stale_after_seconds=60)
            self.assertTrue(claimed)
            self.assertTrue(recovered)
            self.assertEqual(repo.get_status(file_key), "processing")


if __name__ == "__main__":
    unittest.main()
