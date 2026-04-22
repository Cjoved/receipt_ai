import unittest

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
        self.assertEqual(post_login_route_value(["admin"]), "/files")
        self.assertEqual(post_login_route_value(["user"]), "/chat")
