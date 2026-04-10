import tempfile
import unittest

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.models import ExtractionRequest
from receipt_ai.features.extraction.orchestrator import ExtractionOrchestrator
from receipt_ai.features.extraction.postprocess.normalize_text import normalize_text


class ExtractionCoreTests(unittest.TestCase):
    def test_normalize_text_collapses_extra_blank_lines(self):
        self.assertEqual(normalize_text("a\r\n\r\n\r\nb\r\n"), "a\n\nb")

    def test_csv_extraction_and_txt_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ExtractionConfig(
                enable_on_upload=True,
                enable_txt_output=True,
                output_dir=tmp,
                max_extract_bytes=15_000_000,
                max_sheet_rows=500,
                max_sheet_cols=64,
                kimi_api_key="",
            )
            orchestrator = ExtractionOrchestrator(config)
            request = ExtractionRequest(
                filename="receipt.csv",
                content_type="text/csv",
                file_bytes=b"item,total\nrice,120\n",
                storage_folder="My Files",
            )
            result = orchestrator.extract(request)
            self.assertEqual(result.status, "success")
            self.assertIn("item | total", result.text)
            self.assertTrue(result.output_path.endswith(".txt"))

    def test_unsupported_file_type_returns_failed_result(self):
        config = ExtractionConfig(enable_txt_output=False, kimi_api_key="")
        orchestrator = ExtractionOrchestrator(config)
        request = ExtractionRequest(
            filename="archive.zip",
            content_type="application/zip",
            file_bytes=b"PK",
            storage_folder="My Files",
        )
        result = orchestrator.extract(request)
        self.assertEqual(result.status, "failed")
        self.assertIn("Unsupported file type", result.error)


if __name__ == "__main__":
    unittest.main()
