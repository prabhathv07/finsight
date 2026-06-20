"""Run the analysis for a day and log it.

Every call writes exactly one briefing row. If the model errors, the row is
still written with status failed and the error text, and the reader gets a
plain fallback instead of nothing. That guarantee is what makes the
briefings table trustworthy as a monitoring source.
"""

import datetime as dt
import time

from analysis.llm import GeminiCommentator
from analysis.store import save_briefing
from analysis.summary import build_summary
from core.config import get_settings


def _fallback(run_date):
    return (
        f"Automated commentary was unavailable for {run_date.isoformat()}. "
        "The underlying market data was still collected and is available in "
        "the briefing input."
    )


def generate_and_store(session, run_date=None, commentator=None, embedder=None):
    run_date = run_date or dt.date.today()
    summary = build_summary(session, run_date)

    if commentator is None:
        settings = get_settings()
        commentator = GeminiCommentator(settings.gemini_api_key, settings.gemini_model)

    model_name = getattr(commentator, "model", "unknown")

    started = time.perf_counter()
    status, error, output = "ok", None, ""
    try:
        output = commentator(summary)
    except Exception as exc:
        status = "failed"
        error = str(exc)
        output = _fallback(run_date)
    latency_ms = int((time.perf_counter() - started) * 1000)

    briefing = save_briefing(
        session, run_date, model_name, summary, output, latency_ms, status, error
    )

    # Index the briefing for retrieval. Best-effort: an embedding failure
    # must never sink the briefing write, which is the system's guarantee.
    if embedder is not None:
        from rag.store import index_briefing

        try:
            session.flush()  # assign briefing.id before chunks reference it
            index_briefing(session, briefing, embedder)
        except Exception:
            pass

    return briefing
