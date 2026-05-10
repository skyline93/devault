from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from devault.settings import Settings

logger = logging.getLogger(__name__)


def send_plain_email(settings: Settings, *, to_addr: str, subject: str, body: str) -> None:
    """§十六-10: SMTP when configured; otherwise log-only (dev / air-gapped)."""
    host = (settings.smtp_host or "").strip()
    if not host:
        logger.warning("SMTP not configured; email to %s subject=%r skipped", to_addr, subject)
        logger.info("email_body:\n%s", body)
        return
    port = int(settings.smtp_port or 587)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or "noreply@localhost"
    msg["To"] = to_addr
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        user = (settings.smtp_user or "").strip()
        if user and settings.smtp_password:
            smtp.login(user, settings.smtp_password)
        smtp.send_message(msg)
