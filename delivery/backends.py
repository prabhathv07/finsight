"""Email backends.

Two real backends sit behind one send(subject, html, recipient) method:
SMTP for local Gmail, Resend for production. The factory picks one from
config. Tests pass their own object with the same method and assert on what
it captured, so no mail ever leaves during a test.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class SMTPBackend:
    name = "smtp"

    def __init__(self, host, port, user, password, sender):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender

    def send(self, subject, body_html, recipient):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = recipient
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP_SSL(self.host, self.port, timeout=10) as server:
            server.login(self.user, self.password)
            server.sendmail(self.sender, recipient, msg.as_string())


class ResendBackend:
    name = "resend"

    def __init__(self, api_key, sender):
        self.api_key = api_key
        self.sender = sender

    def send(self, subject, body_html, recipient):
        import resend

        resend.api_key = self.api_key
        resend.Emails.send(
            {
                "from": self.sender,
                "to": recipient,
                "subject": subject,
                "html": body_html,
            }
        )


class BrevoBackend:
    """HTTP email API. Render's free tier blocks outbound SMTP ports
    (25/465/587), so mail from the web service must ride HTTPS instead.
    Brevo's free tier (300/day) verifies a single sender address without
    a custom domain."""

    name = "brevo"

    def __init__(self, api_key, sender):
        self.api_key = api_key
        self.sender = sender

    def send(self, subject, body_html, recipient):
        import json
        import urllib.error
        import urllib.request

        payload = json.dumps({
            "sender": {"email": self.sender, "name": "FinSight"},
            "to": [{"email": recipient}],
            "subject": subject,
            "htmlContent": body_html,
        }).encode()
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=payload,
            headers={"api-key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise RuntimeError(f"brevo rejected the send ({exc.code}): {detail}") from exc


def backend_from_settings(settings):
    if settings.email_backend == "brevo":
        if not settings.brevo_api_key:
            raise RuntimeError("EMAIL_BACKEND is 'brevo' but BREVO_API_KEY is empty")
        if not settings.email_from:
            raise RuntimeError("EMAIL_BACKEND is 'brevo' but EMAIL_FROM is empty")
        return BrevoBackend(settings.brevo_api_key, settings.email_from)
    if settings.email_backend == "resend":
        if not settings.resend_api_key:
            raise RuntimeError("EMAIL_BACKEND is 'resend' but RESEND_API_KEY is empty")
        if not settings.email_from:
            raise RuntimeError("EMAIL_BACKEND is 'resend' but EMAIL_FROM is empty")
        return ResendBackend(settings.resend_api_key, settings.email_from)
    if not (settings.email_user and settings.email_password):
        raise RuntimeError(
            "EMAIL_BACKEND is 'smtp' but EMAIL_USER/EMAIL_PASSWORD are empty"
        )
    return SMTPBackend(
        settings.smtp_host,
        settings.smtp_port,
        settings.email_user,
        settings.email_password,
        settings.email_from,
    )
