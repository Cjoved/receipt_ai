import unittest

from receipt_ai.features.files.validation import validate_upload_filename


class FilesUploadValidationTests(unittest.TestCase):
    def test_svg_is_rejected_for_upload(self):
        err = validate_upload_filename("sample.svg")
        self.assertIsNotNone(err)
        self.assertIn("Unsupported file type", err or "")

    def test_png_is_allowed_for_upload(self):
        err = validate_upload_filename("sample.png")
        self.assertIsNone(err)


if __name__ == "__main__":
    unittest.main()
