import unittest
from pathlib import Path


class AuthStateFlowGuardTests(unittest.TestCase):
    def test_state_has_password_reset_and_verify_handlers(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn("async def request_password_reset(self):", source)
        self.assertIn("async def submit_password_reset(self):", source)
        self.assertIn("async def verify_email(self):", source)
        self.assertIn("async def resend_verification(self):", source)

    def test_state_enforces_admin_only_login(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn("administrator accounts", source.lower())
        self.assertIn("has_role_value(user.roles, \"admin\")", source)

    def test_state_enforces_verification_gate(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn("cfg.require_email_verified", source)
        self.assertIn('return rx.redirect("/verify-email")', source)


if __name__ == "__main__":
    unittest.main()
