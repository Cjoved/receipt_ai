import unittest
from unittest.mock import patch

from receipt_ai.features.extraction.adapters.kimi_vision_core import kimi_try_receipt_page
from receipt_ai.features.extraction.config import ExtractionConfig


class KimiTryReceiptPageTests(unittest.TestCase):
    def test_relax_accepts_text_that_fails_strict_receipt_gate(self) -> None:
        cfg = ExtractionConfig(kimi_api_key="k", require_receipt_signals=True)
        weak = "Some invoice header only.\n" + "x" * 40
        with patch(
            "receipt_ai.features.extraction.adapters.kimi_vision_core.kimi_raw_vision_completion",
            return_value=weak,
        ):
            text, reason = kimi_try_receipt_page(
                cfg,
                image_bytes=b"x",
                mime="image/png",
                prompt_label="doc.pdf (page 2)",
                relax_receipt_validation=True,
            )
        self.assertIsNone(reason)
        self.assertEqual(text, weak)

    def test_strict_still_skips_weak_text(self) -> None:
        cfg = ExtractionConfig(kimi_api_key="k", require_receipt_signals=True)
        weak = "Some invoice header only.\n" + "x" * 40
        with patch(
            "receipt_ai.features.extraction.adapters.kimi_vision_core.kimi_raw_vision_completion",
            return_value=weak,
        ):
            text, reason = kimi_try_receipt_page(
                cfg,
                image_bytes=b"x",
                mime="image/png",
                prompt_label="x.png",
                relax_receipt_validation=False,
            )
        self.assertIsNone(text)
        self.assertEqual(reason, "receipt_validation")


if __name__ == "__main__":
    unittest.main()
