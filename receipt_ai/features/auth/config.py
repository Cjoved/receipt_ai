from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class AuthConfig:
    require_email_verified: bool = True
    session_ttl_hours: int = 24
    reset_token_ttl_minutes: int = 30
    verify_token_ttl_hours: int = 24
    app_base_url: str = "http://localhost:3000"
    email_from: str = "no-reply@receipt.ai"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    auth_rate_limit_window_seconds: int = 60
    auth_rate_limit_login_max_attempts: int = 5
    auth_rate_limit_register_max_attempts: int = 5
    auth_rate_limit_reset_max_attempts: int = 5

    @classmethod
    def from_env(cls) -> "AuthConfig":
        load_dotenv()
        return cls(
            require_email_verified=_env_bool("AUTH_REQUIRE_EMAIL_VERIFIED", True),
            session_ttl_hours=max(1, _env_int("AUTH_SESSION_TTL_HOURS", 24)),
            reset_token_ttl_minutes=max(5, _env_int("AUTH_TOKEN_TTL_RESET_MINUTES", 30)),
            verify_token_ttl_hours=max(1, _env_int("AUTH_TOKEN_TTL_VERIFY_HOURS", 24)),
            app_base_url=os.getenv("APP_BASE_URL", "http://localhost:3000").strip() or "http://localhost:3000",
            email_from=os.getenv("AUTH_EMAIL_FROM", "no-reply@receipt.ai").strip() or "no-reply@receipt.ai",
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=max(1, _env_int("SMTP_PORT", 587)),
            smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
            smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
            smtp_use_tls=_env_bool("SMTP_USE_TLS", True),
            smtp_use_ssl=_env_bool("SMTP_USE_SSL", False),
            auth_rate_limit_window_seconds=max(30, _env_int("AUTH_RATE_LIMIT_WINDOW_SECONDS", 60)),
            auth_rate_limit_login_max_attempts=max(1, _env_int("AUTH_RATE_LIMIT_LOGIN_MAX_ATTEMPTS", 5)),
            auth_rate_limit_register_max_attempts=max(1, _env_int("AUTH_RATE_LIMIT_REGISTER_MAX_ATTEMPTS", 5)),
            auth_rate_limit_reset_max_attempts=max(1, _env_int("AUTH_RATE_LIMIT_RESET_MAX_ATTEMPTS", 5)),
        )
