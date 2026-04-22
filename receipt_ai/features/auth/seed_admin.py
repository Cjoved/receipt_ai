from __future__ import annotations

import asyncio
import os
import re
import sys

from dotenv import load_dotenv

from receipt_ai.features.auth.service import upsert_user


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "on"}


def _looks_like_default_password(value: str) -> bool:
    lowered = value.strip().lower()
    bad = {
        "admin123",
        "password",
        "password123",
        "changeme",
        "123456",
        "qwerty",
    }
    return lowered in bad


def _validate_password(value: str) -> str | None:
    if len(value) < 12:
        return "SEED_ADMIN_PASSWORD must be at least 12 characters."
    if _looks_like_default_password(value):
        return "SEED_ADMIN_PASSWORD is too weak/default-like."
    checks = 0
    checks += int(bool(re.search(r"[a-z]", value)))
    checks += int(bool(re.search(r"[A-Z]", value)))
    checks += int(bool(re.search(r"[0-9]", value)))
    checks += int(bool(re.search(r"[^A-Za-z0-9]", value)))
    if checks < 3:
        return "SEED_ADMIN_PASSWORD must include at least 3 of: lowercase, uppercase, number, symbol."
    return None


def seed_admin() -> None:
    load_dotenv()
    if not _env_bool("ALLOW_SEED", False):
        raise RuntimeError("Seeder blocked. Set ALLOW_SEED=true explicitly to run this command.")
    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    if app_env in {"prod", "production"}:
        raise RuntimeError("Seeder blocked in production environment (APP_ENV=production).")

    email = os.getenv("SEED_ADMIN_EMAIL", "admin@receipt.ai").strip().lower() or "admin@receipt.ai"
    password = os.getenv("SEED_ADMIN_PASSWORD", "")
    if password == "":
        raise RuntimeError("SEED_ADMIN_PASSWORD is required.")
    pw_error = _validate_password(password)
    if pw_error:
        raise RuntimeError(pw_error)

    display_name = os.getenv("SEED_ADMIN_DISPLAY_NAME", "Admin").strip() or "Admin"
    user = asyncio.run(upsert_user(email, password, display_name=display_name, role_names=("admin",)))
    print(f"Seeded admin user (dev-only): {user.email} ({user.display_name})")


if __name__ == "__main__":
    try:
        seed_admin()
    except Exception as exc:
        print(f"Seeder failed: {exc}")
        sys.exit(1)
