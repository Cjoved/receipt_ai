import json
import unittest

from receipt_ai.features.extraction.adapters.kimi_vision_core import (
    _normalize_receipt_payload,
    _receipt_json_to_plain_text,
)


class KimiDateNormalizationTests(unittest.TestCase):
    def test_normalizes_two_digit_year_to_full_iso_date(self) -> None:
        raw = """
        {
          "company_name": "Sample Store",
          "date": "04/18/26",
          "total_amount": 370.0,
          "particulars": ["Meals"],
          "uncertain_fields": []
        }
        """
        text = _receipt_json_to_plain_text(raw)
        self.assertIn("Date: 2026-04-18", text)

    def test_sets_date_null_when_year_is_missing(self) -> None:
        raw = """
        {
          "company_name": "Sample Store",
          "date": "04/18",
          "total_amount": 370.0,
          "particulars": ["Meals"],
          "uncertain_fields": []
        }
        """
        text = _receipt_json_to_plain_text(raw)
        self.assertNotIn("Date:", text)
        self.assertIn("Company Name: Sample Store", text)
        payload = _normalize_receipt_payload(json.loads(raw.strip()))
        self.assertIsNone(payload.get("date"))
        notes = payload.get("uncertain_fields") or []
        self.assertTrue(
            any("year is missing" in n.lower() for n in notes),
            msg=f"expected year-missing note, got {notes!r}",
        )

    def test_prefers_context_year_for_ambiguous_two_digit_ocr_year(self) -> None:
        raw = """
        {
          "company_name": "Sample Store",
          "date": "04/20/24",
          "total_amount": 370.0,
          "particulars": ["Meals"],
          "uncertain_fields": []
        }
        """
        text = _receipt_json_to_plain_text(raw, prompt_label="Screenshot 2026-04-20 160326.png")
        self.assertIn("Date: 2026-04-20", text)

    def test_filename_full_date_corrects_wrong_four_digit_year(self) -> None:
        raw = """
        {
          "company_name": "Jollibee",
          "date": "2024-04-09",
          "total_amount": 418.0,
          "uncertain_fields": []
        }
        """
        text = _receipt_json_to_plain_text(
            raw, prompt_label="C:/uploads/inv_2026-04-09_jollibee.png"
        )
        self.assertIn("Date: 2026-04-09", text)
        payload = _normalize_receipt_payload(
            json.loads(raw.strip()),
            prompt_label="inv_2026-04-09_jollibee.png",
        )
        notes = " ".join(payload.get("uncertain_fields") or [])
        self.assertIn("Year corrected", notes)

    def test_no_year_bump_when_filename_date_differs(self) -> None:
        raw = """
        {
          "company_name": "Sample Store",
          "date": "2024-04-09",
          "total_amount": 100.0,
          "uncertain_fields": []
        }
        """
        text = _receipt_json_to_plain_text(
            raw, prompt_label="Screenshot 2026-04-20 160326.png"
        )
        self.assertIn("Date: 2024-04-09", text)


if __name__ == "__main__":
    unittest.main()
