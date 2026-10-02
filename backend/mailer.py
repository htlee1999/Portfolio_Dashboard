"""Outgoing email (password resets).

Sends through SMTP when SMTP_HOST is configured. Otherwise the message is
printed to the API server's console, which keeps password recovery working
on a local install with no mail server: only someone with access to the
machine running the API can read it.
"""

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger("uvicorn.error")


def smtp_configured() -> bool:
    """True when there's a host, and a password whenever a login user is set."""
    if not os.getenv("SMTP_HOST"):
        return False
    return not os.getenv("SMTP_USER") or bool(os.getenv("SMTP_PASSWORD"))


def app_url() -> str:
    return os.getenv("APP_URL", "http://localhost:3000").rstrip("/")


def _tls_context() -> ssl.SSLContext:
    # Prefer certifi's CA bundle: the python.org macOS build ships without system roots.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _send_smtp(to: str, subject: str, text: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or user or f"no-reply@{host}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(text)

    context = _tls_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as smtp:
            if user:
                smtp.login(user, password or "")
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls(context=context)
            if user:
                smtp.login(user, password or "")
            smtp.send_message(msg)


def send_test(to: str) -> None:
    """Send a test message, raising on failure (used by `backend.manage test-email`)."""
    if not smtp_configured():
        raise RuntimeError("SMTP isn't fully configured: set SMTP_HOST, SMTP_USER and SMTP_PASSWORD in .env")
    _send_smtp(to, "Portfolio Dashboard test email", "Email delivery is working. Password reset links will arrive like this.\n")


def send_password_reset(username: str, email: str | None, link: str, minutes: int) -> str:
    """Deliver a reset link. Returns "email" or "console" (where it went)."""
    text = (
        f"Hi {username},\n\n"
        "Someone asked to reset the password for your Portfolio Dashboard account.\n"
        f"Open this link within {minutes} minutes to choose a new password:\n\n"
        f"{link}\n\n"
        "If you didn't ask for this, ignore this email. Your password won't change.\n"
    )
    if smtp_configured() and email:
        try:
            _send_smtp(email, "Reset your Portfolio Dashboard password", text)
            return "email"
        except Exception as e:  # fall back to the console so recovery still works
            log.error("Password reset email to %s failed: %s", email, e)
    banner = "=" * 72
    log.warning("\n%s\nPASSWORD RESET for '%s' (expires in %d min):\n%s\n%s", banner, username, minutes, link, banner)
    return "console"
