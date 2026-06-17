"""Daily pipeline steps.

Split into ingest and compute so the orchestrator can retry each on its own
and the command-line runner can call both in one shot. Both steps hit the
network through the provider, so both are worth retrying in the flow.
"""

import datetime as dt

from features.indicators import indicator_set
from features.sparkline import sparkline
from features.store import save_indicator
from ingestion import universe
from ingestion.daily_pull import history_for, pull
from ingestion.store import save_quotes


def ingest(session, run_date=None, provider=None):
    run_date = run_date or dt.date.today()
    tagged = pull(provider=provider)
    return save_quotes(session, run_date, tagged)


def compute(session, run_date=None, provider=None):
    run_date = run_date or dt.date.today()
    study_symbols = universe.WATCHLIST + universe.SECTORS
    histories = history_for(study_symbols, provider=provider)

    written = 0
    for symbol, prices in histories.items():
        if not prices:
            continue
        values = indicator_set(prices)
        spark = sparkline(prices[-20:])
        save_indicator(session, run_date, symbol, values, spark)
        written += 1
    return written


def run(session, run_date=None, provider=None):
    run_date = run_date or dt.date.today()
    quotes_written = ingest(session, run_date, provider)
    indicators_written = compute(session, run_date, provider)
    return {
        "run_date": run_date,
        "quotes_written": quotes_written,
        "indicators_written": indicators_written,
    }
