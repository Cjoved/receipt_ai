import unittest
from pathlib import Path


class AuthRoutesAndPagesTests(unittest.TestCase):
    def test_app_has_full_auth_routes(self):
        source = Path("receipt_ai/app.py").read_text(encoding="utf-8")
        self.assertIn('route="/register"', source)
        self.assertIn('route="/forgot-password"', source)
        self.assertIn('route="/reset-password"', source)
        self.assertIn('route="/verify-email"', source)

    def test_new_auth_pages_exist(self):
        for rel in (
            "receipt_ai/pages/register_page.py",
            "receipt_ai/pages/forgot_password_page.py",
            "receipt_ai/pages/reset_password_page.py",
            "receipt_ai/pages/verify_email_page.py",
        ):
            self.assertTrue(Path(rel).exists(), f"Missing file: {rel}")


if __name__ == "__main__":
    unittest.main()
