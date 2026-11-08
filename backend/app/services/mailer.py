"""
app/services/mailer.py
-----------------------
Outgoing email for account links (verification, password reset) and notices.

Uses Python's built-in smtplib -- no extra package. Configured from .env
(SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS,
SMTP_USE_SSL). With SMTP_HOST empty -- local development -- the message,
link included, is printed to the backend terminal instead of being sent.

Callers queue send_email() as a background task, so a request's response
time does not depend on whether an email went out (which would reveal
whether an address has an account).
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        # Development: no mail server. Print the whole message so the link can
        # be followed from the terminal. Never reached once SMTP is configured.
        print(
            "\n" + "=" * 72 +
            f"\n[aiPHeed email -- SMTP_HOST not set, printed instead of sent]"
            f"\nTo: {to}\nSubject: {subject}\n\n{body}\n" + "=" * 72 + "\n",
            flush=True,
        )
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        context = ssl.create_default_context()
        if settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT,
                                      timeout=settings.SMTP_TIMEOUT_SECONDS, context=context)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS)
        with server:
            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                server.starttls(context=context)
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        # The recipient and the error type only: never the body, which holds
        # the link token.
        logger.error("email to %s (%s) failed: %s", to, subject, exc.__class__.__name__)
