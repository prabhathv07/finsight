import datetime as dt

from sqlalchemy import func, select

from core.models import Indicator, RawQuote
from core.pipeline import run
from ingestion.providers.base import Quote
from ingestion.store import save_quotes


def test_save_quotes_inserts_rows(session):
    run_date = dt.date(2026, 1, 5)
    tagged = [
        ("futures", Quote(symbol="ES=F", price=5000.0, change_pct=0.5)),
        ("macro", Quote(symbol="^VIX", price=14.0, change_pct=-1.2)),
    ]
    written = save_quotes(session, run_date, tagged)
    session.commit()

    assert written == 2
    count = session.scalar(select(func.count()).select_from(RawQuote))
    assert count == 2


def test_save_quotes_is_idempotent(session):
    run_date = dt.date(2026, 1, 5)
    tagged = [("futures", Quote(symbol="ES=F", price=5000.0, change_pct=0.5))]

    save_quotes(session, run_date, tagged)
    session.commit()

    # Same run date and symbol, updated price. Should update, not duplicate.
    tagged = [("futures", Quote(symbol="ES=F", price=5010.0, change_pct=0.7))]
    save_quotes(session, run_date, tagged)
    session.commit()

    rows = session.scalars(select(RawQuote)).all()
    assert len(rows) == 1
    assert rows[0].price == 5010.0


def test_pipeline_writes_quotes_and_indicators(session, fake_provider):
    result = run(session, run_date=dt.date(2026, 1, 5), provider=fake_provider)
    session.commit()

    assert result["quotes_written"] > 0
    assert result["indicators_written"] > 0

    quote_count = session.scalar(select(func.count()).select_from(RawQuote))
    indicator_count = session.scalar(select(func.count()).select_from(Indicator))
    assert quote_count == result["quotes_written"]
    assert indicator_count == result["indicators_written"]


def test_pipeline_rerun_does_not_duplicate(session, fake_provider):
    run(session, run_date=dt.date(2026, 1, 5), provider=fake_provider)
    session.commit()
    first = session.scalar(select(func.count()).select_from(RawQuote))

    run(session, run_date=dt.date(2026, 1, 5), provider=fake_provider)
    session.commit()
    second = session.scalar(select(func.count()).select_from(RawQuote))

    assert first == second
