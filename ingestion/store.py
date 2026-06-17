"""Write raw quotes to the database.

Writes are idempotent for a given run date: re-running the morning pull
updates the existing row for a symbol instead of creating duplicates,
which matters when a run is retried after a partial failure.
"""

import datetime as dt

from sqlalchemy import select

from core.models import RawQuote


def save_quotes(session, run_date, tagged_quotes):
    captured_at = dt.datetime.now(dt.UTC)
    written = 0

    for category, quote in tagged_quotes:
        existing = session.scalar(
            select(RawQuote).where(
                RawQuote.run_date == run_date,
                RawQuote.category == category,
                RawQuote.symbol == quote.symbol,
            )
        )

        if existing is None:
            existing = RawQuote(
                run_date=run_date, category=category, symbol=quote.symbol
            )
            session.add(existing)

        existing.captured_at = captured_at
        existing.price = quote.price
        existing.change = quote.change
        existing.change_pct = quote.change_pct
        existing.volume = quote.volume
        existing.extra = quote.extra
        written += 1

    return written
