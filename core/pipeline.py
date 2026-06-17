"""Daily pipeline.

Four steps in order: pull quotes, store them, compute indicators from
recent history, store those. Each step is a plain function so phase 3 can
wrap them in a Prefect flow with retries without rewriting the logic.
"""

import datetime as dt

from features.indicators import indicator_set
from features.sparkline import sparkline
from features.store import save_indicator
from ingestion import universe
from ingestion.daily_pull import history_for, pull
from ingestion.store import save_quotes


def run(session, run_date=None, provider=None):
    run_date = run_date or dt.date.today()

    tagged = pull(provider=provider)
    quotes_written = save_quotes(session, run_date, tagged)

    # Indicators only matter for the symbols a reader actually studies.
    study_symbols = universe.WATCHLIST + universe.SECTORS
    histories = history_for(study_symbols, provider=provider)

    indicators_written = 0
    for symbol, prices in histories.items():
        if not prices:
            continue
        values = indicator_set(prices)
        spark = sparkline(prices[-20:])
        save_indicator(session, run_date, symbol, values, spark)
        indicators_written += 1

    return {
        "run_date": run_date,
        "quotes_written": quotes_written,
        "indicators_written": indicators_written,
    }
