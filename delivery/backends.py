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


def backend_from_settings(settings):
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
