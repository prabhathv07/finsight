import datetime as dt

import pytest

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
