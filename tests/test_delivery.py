import datetime as dt


from delivery.render import render_html, subject_for
from delivery.send import Recipient, send_briefing


class FakeBriefing:
    run_date = dt.date(2026, 1, 6)
    llm_output = "Futures firm.\nVIX easing."


class CapturingBackend:
    def __init__(self):
        self.messages = []

    def send(self, subject, body_html, recipient):
        self.messages.append((subject, recipient, body_html))


class BrokenBackend:
    def send(self, subject, body_html, recipient):
        raise RuntimeError("smtp refused")


def test_render_includes_disclaimer_and_links():
    html = render_html(
        FakeBriefing(),
        unsubscribe_url="https://x.test/unsubscribe?token=abc",
        mailing_address="123 Main St, Frisco TX",
    )
    assert "Not financial advice" in html
    assert "123 Main St, Frisco TX" in html
    assert "unsubscribe?token=abc" in html
    assert "VIX easing" in html


def test_subject_format():
    assert subject_for(FakeBriefing()) == "Pre-Market Intelligence Report - 2026-01-06"


def test_send_to_multiple_recipients():
    backend = CapturingBackend()
    recipients = [Recipient("a@test.com"), Recipient("b@test.com")]
    result = send_briefing(FakeBriefing(), recipients, backend)
    assert result["sent"] == ["a@test.com", "b@test.com"]
    assert result["failed"] == []
    assert len(backend.messages) == 2


def test_send_records_failures_without_stopping():
    result = send_briefing(FakeBriefing(), [Recipient("a@test.com")], BrokenBackend())
    assert result["sent"] == []
    assert result["failed"] == ["a@test.com"]


class _Settings:
    def __init__(self, email_to, base_url="https://x.test"):
        self.email_to = email_to
        self.public_base_url = base_url
        self.mailing_address = "123 Main St"


class _OkBriefing:
    run_date = dt.date(2026, 1, 6)
    llm_output = "Futures firm."
    status = "ok"


class _FailedBriefing:
    run_date = dt.date(2026, 1, 6)
    llm_output = "Automated commentary was unavailable."
    status = "failed"


def _sub(email, token="t"):
    class S:
        pass
    s = S()
    s.email = email
    s.unsubscribe_token = token
    return s


def test_clean_recipients_drops_invalid_and_dedupes():
    from delivery.send import Recipient, clean_recipients

    recips = [
        Recipient("good@gmail.com"),
        Recipient("test500@example.com"),   # reserved -> dropped
        Recipient("Good@Gmail.com"),        # duplicate (case) -> dropped
        Recipient("also@reader.io"),
    ]
    cleaned = clean_recipients(recips)
    emails = [r.email for r in cleaned]
    assert "test500@example.com" not in [e.lower() for e in emails]
    assert len(cleaned) == 2


def test_deliver_skips_bad_confirmed_subscriber(monkeypatch):
    from delivery import send as send_mod
    from delivery import subscribers as subs_mod

    monkeypatch.setattr(
        subs_mod, "confirmed",
        lambda session: [_sub("test500@example.com"), _sub("real@gmail.com")],
    )
    backend = CapturingBackend()
    result = send_mod.deliver(None, _OkBriefing(), _Settings(email_to=[]), backend=backend)
    assert result["sent"] == ["real@gmail.com"]
    assert all("example.com" not in m[1] for m in backend.messages)


def test_deliver_failed_briefing_goes_to_admin_only(monkeypatch):
    from delivery import send as send_mod
    from delivery import subscribers as subs_mod

    monkeypatch.setattr(
        subs_mod, "confirmed",
        lambda session: [_sub("real@gmail.com")],
    )
    backend = CapturingBackend()
    result = send_mod.deliver(
        None, _FailedBriefing(), _Settings(email_to=["admin@gmail.com"]), backend=backend
    )
    # Subscriber must NOT receive a broken briefing; only the admin is alerted.
    assert result["sent"] == ["admin@gmail.com"]
    assert "real@gmail.com" not in result["sent"]


# ---- Backend factory misconfiguration -------------------------------------

def test_resend_without_key_fails_loudly(monkeypatch):
    import pytest as _pytest

    from core.config import Settings
    from delivery.backends import backend_from_settings

    monkeypatch.setenv("EMAIL_BACKEND", "resend")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    with _pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        backend_from_settings(Settings())


def test_smtp_without_credentials_fails_loudly(monkeypatch):
    import pytest as _pytest

    from core.config import Settings
    from delivery.backends import backend_from_settings

    monkeypatch.setenv("EMAIL_BACKEND", "smtp")
    for var in ("EMAIL_USER", "EMAIL_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    with _pytest.raises(RuntimeError, match="EMAIL_USER"):
        backend_from_settings(Settings())
