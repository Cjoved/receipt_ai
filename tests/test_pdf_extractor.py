import unittest
from unittest.mock import patch

from receipt_ai.features.extraction.adapters.pdf_extractor import PdfExtractor
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.errors import ExternalAIError
from receipt_ai.features.extraction.models import ExtractionRequest


def _pdf_request(file_bytes: bytes = b"%PDF-1.4\n") -> ExtractionRequest:
    return ExtractionRequest(
        filename="scan.pdf",
        content_type="application/pdf",
        file_bytes=file_bytes,
        storage_folder="Folder",
    )


class PdfExtractorTests(unittest.TestCase):
    def test_auto_uses_pypdf_when_text_long_enough(self) -> None:
        config = ExtractionConfig(
            pdf_extraction_mode="auto",
            pdf_auto_min_text_chars=50,
        )
        ext = PdfExtractor(config)
        req = _pdf_request()
        long_text = "x" * 80
        with patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.extract_text_pypdf",
            return_value=f"--- Page 1 ---\n{long_text}",
        ) as pypdf_mock, patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.render_pdf_pages_to_png_bytes",
        ) as render_mock:
            out = ext.extract(req)
        pypdf_mock.assert_called_once()
        render_mock.assert_not_called()
        self.assertEqual(ext.name, "pypdf")
        self.assertIn(long_text, out)

    def test_auto_falls_back_to_vision_when_text_short(self) -> None:
        config = ExtractionConfig(
            kimi_api_key="sk-test",
            pdf_extraction_mode="auto",
            pdf_auto_min_text_chars=100,
        )
        ext = PdfExtractor(config)
        req = _pdf_request()
        with patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.extract_text_pypdf",
            return_value="short",
        ), patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.render_pdf_pages_to_png_bytes",
            return_value=[b"\x89PNG\r\n\x1a\nfake"],
        ) as render_mock, patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.kimi_try_receipt_page",
            return_value=("Merchant ABC\nTotal 9.99", None),
        ) as kimi_mock:
            out = ext.extract(req)
        render_mock.assert_called_once()
        self.assertEqual(kimi_mock.call_count, 1)
        self.assertEqual(ext.name, "kimi-vision-pdf")
        self.assertIn("--- Page 1 ---", out)
        self.assertIn("Merchant ABC", out)

    def test_vision_all_pages_skipped_raises(self) -> None:
        config = ExtractionConfig(
            kimi_api_key="sk-test",
            pdf_extraction_mode="vision",
        )
        ext = PdfExtractor(config)
        req = _pdf_request()
        with patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.render_pdf_pages_to_png_bytes",
            return_value=[b"png1", b"png2"],
        ), patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.kimi_try_receipt_page",
            return_value=(None, "not_receipt"),
        ):
            with self.assertRaises(ExternalAIError) as ctx:
                ext.extract(req)
        self.assertIn("No usable receipt text", str(ctx.exception))

    def test_text_mode_skips_vision(self) -> None:
        config = ExtractionConfig(
            pdf_extraction_mode="text",
        )
        ext = PdfExtractor(config)
        req = _pdf_request()
        with patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.extract_text_pypdf",
            return_value="only digital text",
        ) as pypdf_mock, patch(
            "receipt_ai.features.extraction.adapters.pdf_extractor.render_pdf_pages_to_png_bytes",
        ) as render_mock:
            out = ext.extract(req)
        pypdf_mock.assert_called_once()
        render_mock.assert_not_called()
        self.assertEqual(ext.name, "pypdf")
        self.assertEqual(out, "only digital text")
