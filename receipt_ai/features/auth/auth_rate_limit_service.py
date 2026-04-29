from __future__ import annotations

import threading
import time

from receipt_ai.features.auth.config import AuthConfig


_LOCK = threading.Lock()
_ATTEMPTS: dict[str, list[float]] = {}


def _track(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    now = time.time()
    cutoff = now - max(1, window_seconds)
    with _LOCK:
        bucket = [t for t in _ATTEMPTS.get(key, []) if t >= cutoff]
        if len(bucket) >= max(1, limit):
            retry_after = int(max(1.0, min(bucket) + max(1, window_seconds) - now))
            _ATTEMPTS[key] = bucket
            return False, retry_after
        bucket.append(now)
        _ATTEMPTS[key] = bucket
    return True, 0


def clear_rate_limit(key: str) -> None:
    with _LOCK:
        _ATTEMPTS.pop(key, None)


def check_login_rate_limit(identity_key: str, config: AuthConfig | None = None) -> tuple[bool, int]:
    cfg = config or AuthConfig.from_env()
    return _track(
        f"login:{identity_key}",
        limit=cfg.auth_rate_limit_login_max_attempts,
        window_seconds=cfg.auth_rate_limit_window_seconds,
    )


def check_register_rate_limit(identity_key: str, config: AuthConfig | None = None) -> tuple[bool, int]:
    cfg = config or AuthConfig.from_env()
    return _track(
        f"register:{identity_key}",
        limit=cfg.auth_rate_limit_register_max_attempts,
        window_seconds=cfg.auth_rate_limit_window_seconds,
    )


def check_reset_rate_limit(identity_key: str, config: AuthConfig | None = None) -> tuple[bool, int]:
    cfg = config or AuthConfig.from_env()
    return _track(
        f"reset:{identity_key}",
        limit=cfg.auth_rate_limit_reset_max_attempts,
        window_seconds=cfg.auth_rate_limit_window_seconds,
    )
