"""Send a stored briefing to recipients.

A recipient is an object with an email and an optional unsubscribe_url, so
this works both for the fixed list used before subscriber management exists
and for confirmed subscribers with per-person unsubscribe tokens later. A
failed send to one address does not stop the rest.
"""

from dataclasses import dataclass

from delivery.render import render_html, subject_for


@dataclass
class Recipient:
    email: str
    unsubscribe_url: str | None = None


def send_briefing(briefing, recipients, backend, mailing_address=None):
    subject = subject_for(briefing)
    sent, failed = [], []

    for recipient in recipients:
        body = render_html(
            briefing,
            unsubscribe_url=recipient.unsubscribe_url,
            mailing_address=mailing_address,
        )
        try:
            backend.send(subject, body, recipient.email)
            sent.append(recipient.email)
        except Exception:
            failed.append(recipient.email)

    return {"sent": sent, "failed": failed}


def subscriber_recipients(subscribers, base_url):
    """Map confirmed subscribers to recipients with per-person unsubscribe links."""
    base = base_url.rstrip("/")
    return [
        Recipient(
            email=sub.email,
            unsubscribe_url=f"{base}/unsubscribe?token={sub.unsubscribe_token}",
        )
        for sub in subscribers
    ]


def deliver(session, briefing, settings, backend=None):
    """Send a briefing to confirmed subscribers plus the configured admin list.

    Shared by the Prefect flow and the one-shot runner so the recipient rules
    live in one place.
    """
    from delivery import subscribers
    from delivery.backends import backend_from_settings

    if briefing is None:
        return {"sent": [], "failed": [], "note": "no briefing to send"}

    recipients = subscriber_recipients(
        subscribers.confirmed(session), settings.public_base_url
    )
    recipients += [Recipient(email=addr) for addr in settings.email_to]
    if not recipients:
        return {"sent": [], "failed": [], "note": "no recipients"}

    backend = backend or backend_from_settings(settings)
    return send_briefing(briefing, recipients, backend, settings.mailing_address)
