"""FastAPI service.

Exposes the analysis run and the stored briefings. The commentator and the
session are injected as dependencies so tests can override them with a fake
model and a throwaway database.
"""

import datetime as dt

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse

from analysis.llm import GeminiCommentator
from analysis.service import generate_and_store
from analysis.store import briefing_for, latest_briefing
from core.config import get_settings
from core.db import get_session_factory
from dashboard.page import render_message, render_page
from delivery import subscribers
from delivery.backends import backend_from_settings
from delivery.render import confirmation_subject, render_confirmation

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


def get_backend():
    return backend_from_settings(get_settings())


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


@app.get("/", response_class=HTMLResponse)
def home(session=Depends(get_session)):
    briefing = latest_briefing(session)
    settings = get_settings()
    count = subscribers.confirmed_count(session)
    return render_page(briefing, count, settings.mailing_address)


@app.post("/subscribe", response_class=HTMLResponse)
def subscribe(email: str = Form(...), session=Depends(get_session),
              backend=Depends(get_backend)):
    settings = get_settings()
    sub, is_new = subscribers.request_subscription(session, email)
    session.flush()

    if is_new:
        confirm_url = f"{settings.public_base_url.rstrip('/')}/confirm?token={sub.confirm_token}"
        body = render_confirmation(confirm_url, settings.mailing_address)
        try:
            backend.send(confirmation_subject(), body, sub.email)
        except Exception:
            # Do not fail the request on a mail hiccup; the address is saved
            # and a later confirm resend can recover it.
            pass

    # Same response whether or not the address was already on file, so the
    # page does not reveal who is subscribed.
    return render_message(
        "Check your inbox",
        "If that address is new, a confirmation link is on its way. "
        "Click it to start receiving the briefing.",
    )


@app.get("/confirm", response_class=HTMLResponse)
def confirm(token: str, session=Depends(get_session)):
    sub = subscribers.confirm(session, token)
    if sub is None:
        return render_message("Link not recognized", "That confirmation link is not valid.")
    return render_message("You are subscribed", "You will get the next briefing by email.")


@app.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(token: str, session=Depends(get_session)):
    sub = subscribers.unsubscribe(session, token)
    if sub is None:
        return render_message("Link not recognized", "That unsubscribe link is not valid.")
    return render_message("You are unsubscribed", "You will not receive further briefings.")
