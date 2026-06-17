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
