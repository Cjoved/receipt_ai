"""Reflex entrypoint expected by rxconfig.app_name."""

from receipt_ai.app import create_app

app = create_app()
