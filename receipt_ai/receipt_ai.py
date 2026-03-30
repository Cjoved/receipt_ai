"""Reflex entrypoint expected by rxconfig.app_name.

Design tokens and shell styling live under ``receipt_ai.core.theme``; the app
factory is :func:`receipt_ai.app.create_app`.
"""

from receipt_ai.app import create_app

app = create_app()
