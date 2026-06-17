"""Run the whole briefing once: ingest, compute, analyze, deliver.

No orchestration server needed, so this is what the GitHub Actions fallback
schedule calls and what you run by hand. The Prefect flow in infra/flow.py is
the scheduled-with-retries path; this is the plain one.

    python run_briefing.py
"""

import datetime as dt

from analysis.service import generate_and_store
from analysis.store import briefing_for
from core.config import get_settings
from core.db import session_scope
from core.models import create_all
from core.pipeline import run as run_pipeline
from delivery.send import deliver


def main(run_date=None):
    run_date = run_date or dt.date.today()
    create_all()

    with session_scope() as session:
        pulled = run_pipeline(session, run_date=run_date)

    with session_scope() as session:
        briefing = generate_and_store(session, run_date=run_date)
        status = briefing.status

    settings = get_settings()
    with session_scope() as session:
        briefing = briefing_for(session, run_date)
        sent = deliver(session, briefing, settings)

    print(
        f"{run_date}: {pulled['quotes_written']} quotes, "
        f"{pulled['indicators_written']} indicators, analysis {status}, "
        f"delivered {len(sent.get('sent', []))}"
    )


if __name__ == "__main__":
    main()
