import unittest
from pathlib import Path


class AuthStateFlowGuardTests(unittest.TestCase):
    def test_state_has_register_reset_verify_handlers(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn("async def register(self):", source)
        self.assertIn("async def request_password_reset(self):", source)
        self.assertIn("async def submit_password_reset(self):", source)
        self.assertIn("async def verify_email(self):", source)
        self.assertIn("async def resend_verification(self):", source)

    def test_state_enforces_verification_gate(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn("cfg.require_email_verified", source)
        self.assertIn('return rx.redirect("/verify-email")', source)


if __name__ == "__main__":
    unittest.main()
