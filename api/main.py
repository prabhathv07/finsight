"""FastAPI service.

Exposes the analysis run and the stored briefings. The commentator and the
session are injected as dependencies so tests can override them with a fake
model and a throwaway database.
"""

import datetime as dt

from fastapi import Depends, FastAPI, HTTPException

from analysis.llm import GeminiCommentator
from analysis.service import generate_and_store
from analysis.store import briefing_for, latest_briefing
from core.config import get_settings
from core.db import get_session_factory

app = FastAPI(title="FinSight")


def get_session():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_commentator():
    settings = get_settings()
    return GeminiCommentator(settings.gemini_api_key, settings.gemini_model)


def _serialize(briefing):
    return {
        "run_date": briefing.run_date.isoformat(),
        "created_at": briefing.created_at.isoformat() if briefing.created_at else None,
        "model_name": briefing.model_name,
        "status": briefing.status,
        "latency_ms": briefing.latency_ms,
        "summary_input": briefing.summary_input,
        "commentary": briefing.llm_output,
        "error": briefing.error,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/briefings/run")
def run_briefing(run_date: str | None = None, session=Depends(get_session),
                 commentator=Depends(get_commentator)):
    parsed = dt.date.fromisoformat(run_date) if run_date else dt.date.today()
    briefing = generate_and_store(session, run_date=parsed, commentator=commentator)
    session.flush()
    return _serialize(briefing)


@app.get("/briefings/latest")
def get_latest(session=Depends(get_session)):
    briefing = latest_briefing(session)
    if briefing is None:
        raise HTTPException(status_code=404, detail="no briefings yet")
    return _serialize(briefing)


@app.get("/briefings/{run_date}")
def get_one(run_date: str, session=Depends(get_session)):
    parsed = dt.date.fromisoformat(run_date)
    briefing = briefing_for(session, parsed)
    if briefing is None:
        raise HTTPException(status_code=404, detail="no briefing for that date")
    return _serialize(briefing)
