"""Send a stored briefing to recipients.

A recipient is an object with an email and an optional unsubscribe_url, so
this works both for the fixed list used before subscriber management exists
and for confirmed subscribers with per-person unsubscribe tokens later. A
failed send to one address does not stop the rest.
"""

import logging
from dataclasses import dataclass

from delivery.render import render_html, subject_for
from delivery.validation import is_valid_email, normalize_email

logger = logging.getLogger("finsight.delivery")


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
            # Log the reason so a delivery failure is visible in the logs
            # instead of vanishing silently.
            logger.exception("send failed for %s", recipient.email)
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


def clean_recipients(recipients):
    """Drop invalid/undeliverable addresses and de-duplicate case-insensitively.

    This is the safety net that keeps a bad row already in the database -- or a
    typo in EMAIL_TO -- from being mailed every day and bouncing. The first
    occurrence of an address wins so its unsubscribe link is preserved.
    """
    seen = set()
    cleaned = []
    for r in recipients:
        email = normalize_email(r.email)
        if not is_valid_email(email):
            logger.warning("skipping undeliverable recipient %r", r.email)
            continue
        if email in seen:
            continue
        seen.add(email)
        cleaned.append(r)
    return cleaned


def deliver(session, briefing, settings, backend=None):
    """Send a briefing to confirmed subscribers plus the configured admin list.

    Two guards protect subscribers and the sender's reputation:
      * A briefing whose analysis failed (status != "ok") is a fallback notice,
        not a real briefing, so it goes only to the admin EMAIL_TO list as an
        alert -- subscribers are never sent a broken briefing.
      * Every recipient list is validated and de-duplicated before sending, so
        undeliverable or repeated addresses cannot bounce or double-send.
    """
    from delivery import subscribers
    from delivery.backends import backend_from_settings

    if briefing is None:
        return {"sent": [], "failed": [], "note": "no briefing to send"}

    admin = [Recipient(email=addr) for addr in settings.email_to]

    if getattr(briefing, "status", "ok") != "ok":
        logger.warning(
            "briefing %s has status %r; alerting admin only, not subscribers",
            getattr(briefing, "run_date", "?"), briefing.status,
        )
        recipients = admin
    else:
        recipients = subscriber_recipients(
            subscribers.confirmed(session), settings.public_base_url
        ) + admin

    recipients = clean_recipients(recipients)
    if not recipients:
        return {"sent": [], "failed": [], "note": "no recipients"}

    backend = backend or backend_from_settings(settings)
    return send_briefing(briefing, recipients, backend, settings.mailing_address)
