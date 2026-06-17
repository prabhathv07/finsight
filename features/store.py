"""Write computed indicators to the database, idempotent per run date."""

import datetime as dt

from sqlalchemy import select

from core.models import Indicator


def save_indicator(session, run_date, symbol, values, sparkline=None):
    existing = session.scalar(
        select(Indicator).where(
            Indicator.run_date == run_date, Indicator.symbol == symbol
        )
    )

    if existing is None:
        existing = Indicator(run_date=run_date, symbol=symbol)
        session.add(existing)

    existing.computed_at = dt.datetime.now(dt.UTC)
    existing.rsi = values.get("rsi")
    existing.ma9 = values.get("ma9")
    existing.ma20 = values.get("ma20")
    existing.ma50 = values.get("ma50")
    existing.sparkline = sparkline
    return existing
