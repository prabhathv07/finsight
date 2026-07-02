"""Subscriber store.

Double opt-in is enforced here, not at the edge: a new signup is always
pending until the confirm token comes back. Tokens are random and url-safe.
Re-subscribing an unsubscribed address puts it back to pending with fresh
tokens rather than silently re-enrolling it.
"""

import datetime as dt
import secrets

from sqlalchemy import select

from core.models import Subscriber
from delivery.validation import is_valid_email, normalize_email


def _token():
    return secrets.token_urlsafe(24)


def request_subscription(session, email):
    """Create or reset a pending subscription. Returns (subscriber, is_new).

    is_new is True when a confirmation email should be sent: a brand new
    address or one that had unsubscribed. An address already pending or
    confirmed is left as-is and is_new is False, so repeat submits do not
    spam a confirmation link.
    """
    email = normalize_email(email)
    if not is_valid_email(email):
        raise ValueError("invalid email address")
    existing = session.scalar(select(Subscriber).where(Subscriber.email == email))

    if existing is None:
        sub = Subscriber(
            email=email,
            status="pending",
            confirm_token=_token(),
            unsubscribe_token=_token(),
            created_at=dt.datetime.now(dt.UTC),
        )
        session.add(sub)
        return sub, True

    if existing.status == "unsubscribed":
        existing.status = "pending"
        existing.confirm_token = _token()
        existing.unsubscribe_token = _token()
        existing.created_at = dt.datetime.now(dt.UTC)
        existing.confirmed_at = None
        return existing, True

    return existing, False


def refresh_confirmation(session, email):
    """Refresh the confirm token for a pending subscriber.

    Returns (subscriber, True) when the address is pending and a new
    confirmation email should be sent. Returns (None, False) otherwise —
    address unknown, already confirmed, or unsubscribed — so the endpoint
    can give the same generic response either way without leaking status.
    """
    email = normalize_email(email)
    existing = session.scalar(select(Subscriber).where(Subscriber.email == email))
    if existing is None or existing.status != "pending":
        return None, False
    existing.confirm_token = _token()
    return existing, True


def confirm(session, token):
    sub = session.scalar(
        select(Subscriber).where(Subscriber.confirm_token == token)
    )
    if sub is None:
        return None
    if sub.status != "confirmed":
        sub.status = "confirmed"
        sub.confirmed_at = dt.datetime.now(dt.UTC)
    return sub


def unsubscribe(session, token):
    sub = session.scalar(
        select(Subscriber).where(Subscriber.unsubscribe_token == token)
    )
    if sub is None:
        return None
    sub.status = "unsubscribed"
    return sub


def confirmed(session):
    return session.scalars(
        select(Subscriber).where(Subscriber.status == "confirmed")
    ).all()


def confirmed_count(session):
    return len(confirmed(session))
