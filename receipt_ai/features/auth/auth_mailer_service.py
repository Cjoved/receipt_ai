from __future__ import annotations

from email.message import EmailMessage
import logging
import smtplib

from receipt_ai.features.auth.config import AuthConfig

logger = logging.getLogger(__name__)


def send_email(*, to_email: str, subject: str, body_text: str, config: AuthConfig | None = None) -> None:
    cfg = config or AuthConfig.from_env()
    recipient = to_email.strip().lower()
    if not recipient:
        return

    if not cfg.smtp_host:
        logger.info("auth_mail_dev_sink to=%s subject=%s body=%s", recipient, subject, body_text)
        return

    msg = EmailMessage()
    msg["From"] = cfg.email_from
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body_text)

    if cfg.smtp_use_ssl:
        with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=30) as client:
            if cfg.smtp_username:
                client.login(cfg.smtp_username, cfg.smtp_password)
            client.send_message(msg)
        return

    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as client:
        if cfg.smtp_use_tls:
            client.starttls()
        if cfg.smtp_username:
            client.login(cfg.smtp_username, cfg.smtp_password)
        client.send_message(msg)
