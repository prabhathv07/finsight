"""Daily briefing flow.

Replaces the GitHub Actions cron. Four tasks run in order: ingest, compute,
analyze, deliver. The three that reach an external service retry on failure.
Each task opens its own session so a retry starts from a clean transaction.

Run it on a schedule locally with:

    python -m infra.flow

That serves the flow with a weekday cron at 9:00 AM Central. In production
the same flow is deployed to a Prefect worker. The schedule string assumes
Central time; adjust the cron if the worker runs in UTC.
"""

import datetime as dt

from prefect import flow, task

from core.config import get_settings
from core.db import session_scope
from core.models import create_all

RETRY = {"retries": 2, "retry_delay_seconds": 30}


@task(**RETRY)
def ingest_task(run_date):
    from core.pipeline import ingest

    with session_scope() as session:
        return ingest(session, run_date)


@task(**RETRY)
def compute_task(run_date):
    from core.pipeline import compute

    with session_scope() as session:
        return compute(session, run_date)


@task(**RETRY)
def analyze_task(run_date):
    from analysis.service import generate_and_store

    with session_scope() as session:
        briefing = generate_and_store(session, run_date)
        return briefing.status


@task
def deliver_task(run_date):
    from analysis.store import briefing_for
    from delivery.backends import backend_from_settings
    from delivery.send import Recipient, send_briefing

    settings = get_settings()
    recipients = [Recipient(email=addr) for addr in settings.email_to]
    if not recipients:
        return {"sent": [], "failed": [], "note": "no recipients configured"}

    with session_scope() as session:
        briefing = briefing_for(session, run_date)
        if briefing is None:
            return {"sent": [], "failed": [], "note": "no briefing to send"}
        backend = backend_from_settings(settings)
        return send_briefing(
            briefing, recipients, backend, settings.mailing_address
        )


@flow(name="finsight-daily-briefing")
def daily_briefing_flow(run_date=None):
    run_date = run_date or dt.date.today()
    create_all()

    ingest_task(run_date)
    compute_task(run_date)
    analyze_task(run_date)
    return deliver_task(run_date)


if __name__ == "__main__":
    daily_briefing_flow.serve(
        name="finsight-daily",
        cron="0 14 * * 1-5",
    )
