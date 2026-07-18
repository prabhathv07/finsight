"""FastAPI service.

Exposes the analysis run and the stored briefings. The commentator and the
session are injected as dependencies so tests can override them with a fake
model and a throwaway database.
"""

import datetime as dt
import logging
import secrets as pysecrets
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from analysis.llm import GeminiCommentator
from analysis.service import generate_and_store
from analysis.store import briefing_for, latest_briefing
from core.config import get_settings
from core.db import get_session_factory
from dashboard.page import render_message, render_page
from delivery import subscribers
from delivery.backends import backend_from_settings
from delivery.render import confirmation_subject, render_confirmation
from rag.answer import GeminiAnswerer
from rag.embed import GeminiEmbedder
from rag.service import answer_question, reindex_all

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="FinSight")
logger = logging.getLogger("finsight.api")

_api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)


def require_api_token(token: str = Security(_api_key_header)):
    """Gate the endpoints that spend Gemini quota behind a shared secret.

    With no FINSIGHT_API_TOKEN configured the endpoints refuse everything:
    forgetting the secret must not silently leave them open.
    """
    expected = get_settings().api_token
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="endpoint disabled: FINSIGHT_API_TOKEN is not configured",
        )
    if not (token and pysecrets.compare_digest(token, expected)):
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Token")


class RateLimiter:
    """Small per-key sliding-window limiter.

    In-memory is enough: the service runs as a single instance, and the goal
    is to stop someone scripting confirmation-email sends at strangers, not
    to survive a distributed flood.
    """

    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self._hits = defaultdict(deque)

    def allow(self, key):
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


_signup_limiter = RateLimiter(limit=5, window_seconds=60)


def limit_signups(request: Request):
    # Render terminates TLS at a proxy; the caller is the first hop in
    # X-Forwarded-For, falling back to the socket peer for local runs.
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    if not _signup_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="too many requests; try again in a minute")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://prabhathv07.github.io"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


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


def get_embedder():
    settings = get_settings()
    return GeminiEmbedder(settings.gemini_api_key, settings.embed_model)


def get_answerer():
    settings = get_settings()
    return GeminiAnswerer(settings.gemini_api_key, settings.gemini_model)


class _BrokenBackend:
    """Placeholder when the mailer is misconfigured.

    Subscribing must still save the row (a later /resend-confirmation can
    recover it), so the config error surfaces on send, where the endpoints
    already log failures, instead of turning the whole request into a 500.
    """

    name = "broken"

    def __init__(self, exc):
        self._exc = exc

    def send(self, subject, body_html, recipient):
        raise RuntimeError(f"mail backend misconfigured: {self._exc}")


def get_backend():
    try:
        return backend_from_settings(get_settings())
    except RuntimeError as exc:
        logger.error("mail backend misconfigured: %s", exc)
        return _BrokenBackend(exc)


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


@app.post("/briefings/run", dependencies=[Depends(require_api_token)])
def run_briefing(run_date: str | None = None, session=Depends(get_session),
                 commentator=Depends(get_commentator),
                 embedder=Depends(get_embedder)):
    parsed = dt.date.fromisoformat(run_date) if run_date else dt.date.today()
    briefing = generate_and_store(
        session, run_date=parsed, commentator=commentator, embedder=embedder
    )
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


@app.post("/subscribe", response_class=HTMLResponse,
          dependencies=[Depends(limit_signups)])
def subscribe(email: str = Form(...), session=Depends(get_session),
              backend=Depends(get_backend)):
    settings = get_settings()
    try:
        sub, is_new = subscribers.request_subscription(session, email)
        session.flush()
    except ValueError:
        # Bad-format address: tell the user so they can fix a typo. This is
        # about the input string, not who is subscribed, so it leaks nothing.
        return render_message(
            "Check your email address",
            "That does not look like a valid email address. "
            "Please check it and try again.",
        )
    except IntegrityError:
        # Two concurrent submits for the same new address: the other request
        # won the unique-constraint race and is sending the confirmation, so
        # this one can return the same generic page.
        session.rollback()
        return render_message(
            "Check your inbox",
            "If that address is new, a confirmation link is on its way. "
            "Click it to start receiving the briefing.",
        )

    if is_new:
        confirm_url = f"{settings.public_base_url.rstrip('/')}/confirm?token={sub.confirm_token}"
        body = render_confirmation(confirm_url, settings.mailing_address)
        try:
            backend.send(confirmation_subject(), body, sub.email)
        except Exception:
            # The address is saved, so a later resend can still recover it --
            # but log the reason instead of swallowing it, or a misconfigured
            # mailer looks identical to success and no confirmation ever lands.
            logger.exception("confirmation email failed for %s", sub.email)

    # Same response whether or not the address was already on file, so the
    # page does not reveal who is subscribed.
    return render_message(
        "Check your inbox",
        "If that address is new, a confirmation link is on its way. "
        "Click it to start receiving the briefing.",
    )


@app.post("/resend-confirmation", response_class=HTMLResponse,
          dependencies=[Depends(limit_signups)])
def resend_confirmation(email: str = Form(...), session=Depends(get_session),
                        backend=Depends(get_backend)):
    settings = get_settings()
    sub, should_send = subscribers.refresh_confirmation(session, email)
    session.flush()

    if should_send:
        confirm_url = f"{settings.public_base_url.rstrip('/')}/confirm?token={sub.confirm_token}"
        body = render_confirmation(confirm_url, settings.mailing_address)
        try:
            backend.send(confirmation_subject(), body, sub.email)
        except Exception:
            logger.exception("confirmation resend failed for %s", sub.email)

    return render_message(
        "Check your inbox",
        "If that address is pending confirmation, a fresh link is on its way.",
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


class AskRequest(BaseModel):
    question: str = Field(max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)


@app.post("/ask", dependencies=[Depends(require_api_token)])
def ask(req: AskRequest, session=Depends(get_session),
        embedder=Depends(get_embedder), answerer=Depends(get_answerer)):
    """Answer a question from the indexed briefing corpus, with citations."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")
    top_k = req.top_k or get_settings().rag_top_k
    try:
        return answer_question(session, question, embedder, answerer, top_k=top_k)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"embedding or answering service error: {exc}") from exc


@app.post("/rag/reindex", dependencies=[Depends(require_api_token)])
def rag_reindex(session=Depends(get_session), embedder=Depends(get_embedder)):
    """Rebuild the chunk corpus from every stored briefing."""
    try:
        return reindex_all(session, embedder)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"embedding service error: {exc}") from exc
