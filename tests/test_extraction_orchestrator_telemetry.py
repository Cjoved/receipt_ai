import unittest
from unittest.mock import patch

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.models import ExtractionRequest
from receipt_ai.features.extraction.orchestrator import ExtractionOrchestrator


class _FakeExtractor:
    name = "kimi-vision-pdf"

    def supports(self, request: ExtractionRequest) -> bool:
        return True

    def extract(self, request: ExtractionRequest) -> str:
        return "--- Page 1 ---\nmerchant: A\ntotal: 1.00"

    last_vision_stats = {
        "pages_total": 3,
        "pages_extracted": 2,
        "pages_skipped": 1,
        "skip_reasons": {"not_receipt": 1},
    }


class _FakeRouter:
    def resolve(self, request: ExtractionRequest):
        return _FakeExtractor()


class ExtractionOrchestratorTelemetryTests(unittest.TestCase):
    def test_orchestrator_copies_pdf_telemetry_to_result(self) -> None:
        cfg = ExtractionConfig(enable_txt_output=False)
        req = ExtractionRequest(
            filename="x.pdf",
            content_type="application/pdf",
            file_bytes=b"%PDF-1.4\n",
            storage_folder="Folder",
        )
        with patch("receipt_ai.features.extraction.orchestrator.build_default_router", return_value=_FakeRouter()):
            orch = ExtractionOrchestrator(cfg)
            result = orch.extract(req)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.pages_total, 3)
        self.assertEqual(result.pages_extracted, 2)
        self.assertEqual(result.pages_skipped, 1)
        self.assertEqual(result.skip_reasons.get("not_receipt"), 1)


if __name__ == "__main__":
    unittest.main()
