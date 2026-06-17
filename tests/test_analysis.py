import datetime as dt

from sqlalchemy import func, select

from analysis.service import generate_and_store
from analysis.summary import build_summary
from core.models import Briefing
from core.pipeline import run

RUN_DATE = dt.date(2026, 1, 6)


class FakeCommentator:
    model = "fake-model"

    def __call__(self, summary_text):
        return "Futures are firm and VIX is easing. Watch semis."


class BrokenCommentator:
    model = "broken-model"

    def __call__(self, summary_text):
        raise RuntimeError("api down")


def _seed(session, fake_provider):
    run(session, run_date=RUN_DATE, provider=fake_provider)
    session.commit()


def test_summary_has_sections(session, fake_provider):
    _seed(session, fake_provider)
    text = build_summary(session, RUN_DATE)
    assert "Pre-market summary for 2026-01-06" in text
    assert "FUTURES" in text
    assert "WATCHLIST" in text
    assert "TOP GAINERS" in text


def test_service_logs_successful_run(session, fake_provider):
    _seed(session, fake_provider)
    briefing = generate_and_store(session, run_date=RUN_DATE, commentator=FakeCommentator())
    session.commit()

    assert briefing.status == "ok"
    assert briefing.model_name == "fake-model"
    assert "semis" in briefing.llm_output
    assert briefing.latency_ms >= 0
    assert briefing.summary_input.startswith("Pre-market summary")
    assert briefing.error is None


def test_service_logs_failure_with_fallback(session, fake_provider):
    _seed(session, fake_provider)
    briefing = generate_and_store(session, run_date=RUN_DATE, commentator=BrokenCommentator())
    session.commit()

    assert briefing.status == "failed"
    assert "api down" in briefing.error
    assert "unavailable" in briefing.llm_output
    # The row is still written, which is the point.
    count = session.scalar(select(func.count()).select_from(Briefing))
    assert count == 1


def test_service_idempotent_per_day(session, fake_provider):
    _seed(session, fake_provider)
    generate_and_store(session, run_date=RUN_DATE, commentator=FakeCommentator())
    session.commit()
    generate_and_store(session, run_date=RUN_DATE, commentator=FakeCommentator())
    session.commit()

    count = session.scalar(select(func.count()).select_from(Briefing))
    assert count == 1
