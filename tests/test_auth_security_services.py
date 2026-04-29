import unittest

from receipt_ai.features.auth.auth_credentials_service import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from receipt_ai.features.auth.auth_rate_limit_service import (
    check_login_rate_limit,
    check_register_rate_limit,
    check_reset_rate_limit,
    clear_rate_limit,
)
from receipt_ai.features.auth.auth_token_service import generate_raw_token, hash_token
from receipt_ai.features.auth.config import AuthConfig


class AuthSecurityServicesTests(unittest.TestCase):
    def test_password_strength_validation(self):
        self.assertIsNotNone(validate_password_strength("short"))
        self.assertIsNotNone(validate_password_strength("alllowercase123"))
        self.assertIsNone(validate_password_strength("StrongPass123!"))

    def test_hash_and_verify_password(self):
        raw = "StrongPass123!"
        digest = hash_password(raw)
        self.assertTrue(verify_password(raw, digest))
        self.assertFalse(verify_password("WrongPass123!", digest))

    def test_token_hash_is_stable_for_same_input(self):
        token = generate_raw_token()
        self.assertEqual(hash_token(token), hash_token(token))
        self.assertNotEqual(hash_token(token), hash_token(generate_raw_token()))

    def test_rate_limit_checks(self):
        cfg = AuthConfig(
            auth_rate_limit_window_seconds=60,
            auth_rate_limit_login_max_attempts=1,
            auth_rate_limit_register_max_attempts=1,
            auth_rate_limit_reset_max_attempts=1,
        )
        allowed1, _ = check_login_rate_limit("user@example.com", cfg)
        allowed2, _ = check_login_rate_limit("user@example.com", cfg)
        self.assertTrue(allowed1)
        self.assertFalse(allowed2)
        clear_rate_limit("login:user@example.com")

        r1, _ = check_register_rate_limit("user@example.com", cfg)
        r2, _ = check_register_rate_limit("user@example.com", cfg)
        self.assertTrue(r1)
        self.assertFalse(r2)
        clear_rate_limit("register:user@example.com")

        p1, _ = check_reset_rate_limit("user@example.com", cfg)
        p2, _ = check_reset_rate_limit("user@example.com", cfg)
        self.assertTrue(p1)
        self.assertFalse(p2)
        clear_rate_limit("reset:user@example.com")


if __name__ == "__main__":
    unittest.main()
