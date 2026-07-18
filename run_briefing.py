"""Run the whole briefing once: ingest, compute, analyze, deliver.

No orchestration server needed, so this is what the GitHub Actions fallback
schedule calls and what you run by hand. The Prefect flow in infra/flow.py is
the scheduled-with-retries path; this is the plain one.

    python run_briefing.py
"""

import datetime as dt
import logging
import sys

from analysis.service import generate_and_store
from analysis.store import briefing_for
from core.config import get_settings
from core.db import session_scope
from core.pipeline import run as run_pipeline
from delivery.send import deliver
from infra.init_db import init as init_db
from rag.embed import GeminiEmbedder


def main(run_date=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_date = run_date or dt.date.today()

    settings = get_settings()
    settings.require_gemini_key()  # a bad key should fail loudly, not per-call

    init_db()  # enables pgvector extension before creating tables

    with session_scope() as session:
        pulled = run_pipeline(session, run_date=run_date)

    embedder = GeminiEmbedder(settings.gemini_api_key, settings.embed_model)
    with session_scope() as session:
        briefing = generate_and_store(session, run_date=run_date, embedder=embedder)
        status = briefing.status

    with session_scope() as session:
        briefing = briefing_for(session, run_date)
        sent = deliver(session, briefing, settings)

    print(
        f"{run_date}: {pulled['quotes_written']} quotes, "
        f"{pulled['indicators_written']} indicators, analysis {status}, "
        f"delivered {len(sent.get('sent', []))}"
    )
    # The fallback email has been delivered by now, but the scheduled job
    # should still show red so a commentary failure is impossible to miss.
    if status != "ok":
        sys.exit(1)


if __name__ == "__main__":
    main()
