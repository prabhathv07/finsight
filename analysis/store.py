"""Write briefing records, idempotent per run date."""

import datetime as dt

from sqlalchemy import select

from core.models import Briefing


def save_briefing(session, run_date, model_name, summary_input, llm_output,
                  latency_ms, status, error=None):
    existing = session.scalar(
        select(Briefing).where(Briefing.run_date == run_date)
    )
    if existing is None:
        existing = Briefing(run_date=run_date)
        session.add(existing)

    existing.created_at = dt.datetime.now(dt.UTC)
    existing.model_name = model_name
    existing.summary_input = summary_input
    existing.llm_output = llm_output
    existing.latency_ms = latency_ms
    existing.status = status
    existing.error = error
    return existing


def latest_briefing(session):
    return session.scalar(
        select(Briefing).order_by(Briefing.run_date.desc())
    )


def briefing_for(session, run_date):
    return session.scalar(
        select(Briefing).where(Briefing.run_date == run_date)
    )
