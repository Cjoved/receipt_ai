import unittest

from receipt_ai.features.extraction.validators.image_receipt_validator import receipt_quality_warnings


class ExtractionValidatorTests(unittest.TestCase):
    def test_receipt_warnings_when_expected_markers_missing(self):
        warnings = receipt_quality_warnings("hello world")
        self.assertGreaterEqual(len(warnings), 2)

    def test_receipt_warnings_are_low_for_receipt_like_text(self):
        text = "Receipt\nDate: 2026-04-08\nSubtotal 100\nTax 12\nTotal 112"
        warnings = receipt_quality_warnings(text)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
