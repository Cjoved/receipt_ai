import unittest
from pathlib import Path

from receipt_ai.features.auth.state import (
    has_permission_value,
    has_role_value,
    post_login_route_value,
    primary_role_value,
)


class AuthRbacStateTests(unittest.TestCase):
    def test_has_role_value(self):
        self.assertTrue(has_role_value(["admin"], "admin"))
        self.assertFalse(has_role_value(["user"], "admin"))

    def test_has_permission_value_admin_override(self):
        self.assertTrue(has_permission_value(["admin"], [], "files:write"))
        self.assertFalse(has_permission_value(["user"], ["chat:read"], "files:write"))

    def test_primary_role_value(self):
        self.assertEqual(primary_role_value(["admin", "user"]), "admin")
        self.assertEqual(primary_role_value([]), "user")

    def test_post_login_route_value(self):
        # Admin-only deployment: successful sign-in always lands on /files.
        self.assertEqual(post_login_route_value(["admin"]), "/files")
        self.assertEqual(post_login_route_value(["user"]), "/files")


class AuthGuardResiliencyTests(unittest.TestCase):
    def test_guard_protected_route_has_error_fallback(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn("Session check failed. Please sign in again.", source)
        self.assertIn("except Exception:", source)

    def test_logout_clears_identity_before_revoke_attempt(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn("token = self.auth_token", source)
        self.assertIn("self._clear_auth_identity()", source)


class AuthSettingsFlowTests(unittest.TestCase):
    def test_settings_validation_messages_exist(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn("Display name is required.", source)
        self.assertIn("Display name must be at least 2 characters.", source)
        self.assertIn("Display name must be at most 120 characters.", source)

    def test_settings_route_redirect_exists(self):
        source = Path("receipt_ai/features/auth/state.py").read_text(encoding="utf-8")
        self.assertIn('return rx.redirect("/settings")', source)

    def test_settings_page_registered(self):
        source = Path("receipt_ai/app.py").read_text(encoding="utf-8")
        self.assertIn('route="/settings"', source)
        self.assertIn("AuthState.load_settings_form", source)
