"""RAG layer tests -- fully offline, no key or network.

A deterministic fake embedder maps text to a vector by hashing tokens into a
small fixed-width bag-of-words, so semantically overlapping texts score higher
together. That is enough to assert retrieval ranks the right briefing first.
"""

import datetime as dt
import hashlib

import pytest
from fastapi.testclient import TestClient

from api.main import app, get_answerer, get_commentator, get_embedder
from core import db
from core.models import Base, BriefingChunk
from rag.chunk import chunk_briefing
from rag.service import answer_question, reindex_all
from rag.store import index_briefing, retrieve

DIM = 64


def _embed_one(text):
    vec = [0.0] * DIM
    for token in text.lower().split():
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % DIM] += 1.0
    return vec


class FakeEmbedder:
    model = "fake-embed"

    def __call__(self, texts):
        return [_embed_one(t) for t in texts]


class FakeAnswerer:
    name = "fake-answer"

    def __call__(self, question, context):
        # Echo the first cited date so tests can assert grounding.
        return f"Based on the briefings: {context[:40]}"


class FakeCommentator:
    model = "fake-model"

    def __call__(self, summary_text):
        return "Semiconductors led the rally while energy lagged badly."


def _make_briefing(session, run_date, summary, commentary):
    from core.models import Briefing

    b = Briefing(
        run_date=run_date,
        created_at=dt.datetime.now(dt.UTC),
        model_name="fake",
        summary_input=summary,
        llm_output=commentary,
        latency_ms=1,
        status="ok",
    )
    session.add(b)
    session.flush()
    return b


# ---- chunking -------------------------------------------------------------

def test_chunk_separates_summary_and_commentary():
    chunks = chunk_briefing(
        "SUMMARY numbers here",
        "Paragraph one runs well past the eighty character minimum so it stands as its own chunk here.\n\n"
        "Paragraph two also runs comfortably past the eighty character minimum so it stays separate too.",
    )
    sources = [c[0] for c in chunks]
    assert sources[0] == "summary"
    assert "commentary" in sources
    assert len(chunks) == 3


def test_chunk_merges_short_fragments():
    chunks = chunk_briefing("", "A real paragraph that is clearly long enough to survive.\n\nshort")
    # The short fragment is folded into the previous chunk.
    assert len(chunks) == 1
    assert "short" in chunks[0][1]


# ---- indexing + retrieval -------------------------------------------------

@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path/'rag.db'}"
    engine = db.reset_engine_for_tests(url)
    Base.metadata.create_all(engine)
    s = db.get_session_factory()()
    try:
        yield s
    finally:
        s.close()


def test_index_writes_chunks(session):
    b = _make_briefing(session, dt.date(2026, 1, 6), "SUMMARY semis strong", "Semiconductors rallied hard on AI demand today.")
    rows = index_briefing(session, b, FakeEmbedder())
    session.commit()
    assert len(rows) >= 2
    assert all(r.embedding is not None for r in rows)
    assert all(r.embed_model == "fake-embed" for r in rows)


def test_index_is_idempotent(session):
    b = _make_briefing(session, dt.date(2026, 1, 6), "SUMMARY", "Energy stocks fell sharply on oversupply worries.")
    index_briefing(session, b, FakeEmbedder())
    session.commit()
    index_briefing(session, b, FakeEmbedder())
    session.commit()
    count = session.query(BriefingChunk).filter_by(briefing_id=b.id).count()
    assert count == len(chunk_briefing(b.summary_input, b.llm_output))


def test_retrieval_ranks_relevant_briefing_first(session):
    b1 = _make_briefing(session, dt.date(2026, 1, 6), "SUMMARY", "Semiconductors and chip makers rallied on strong AI demand.")
    b2 = _make_briefing(session, dt.date(2026, 1, 7), "SUMMARY", "Energy and oil producers slumped on oversupply concerns.")
    index_briefing(session, b1, FakeEmbedder())
    index_briefing(session, b2, FakeEmbedder())
    session.commit()

    query_vec = FakeEmbedder()(["semiconductors chip AI demand rally"])[0]
    results = retrieve(session, query_vec, top_k=1)
    assert results
    top_chunk, score = results[0]
    assert top_chunk.run_date == dt.date(2026, 1, 6)
    assert score > 0


def test_answer_question_returns_sources(session):
    b = _make_briefing(session, dt.date(2026, 1, 6), "SUMMARY", "Semiconductors rallied on AI demand and broad chip strength.")
    index_briefing(session, b, FakeEmbedder())
    session.commit()

    out = answer_question(session, "How did semiconductors do?", FakeEmbedder(), FakeAnswerer(), top_k=3)
    assert out["sources"]
    assert out["sources"][0]["run_date"] == "2026-01-06"
    assert "Based on the briefings" in out["answer"]


def test_answer_with_empty_corpus(session):
    out = answer_question(session, "anything?", FakeEmbedder(), FakeAnswerer())
    assert out["sources"] == []
    assert "no indexed briefings" in out["answer"].lower()


def test_reindex_all(session):
    _make_briefing(session, dt.date(2026, 1, 6), "S1", "Tech led the tape with broad strength across megacaps today.")
    _make_briefing(session, dt.date(2026, 1, 7), "S2", "Financials lagged the market on rate-cut uncertainty today.")
    session.commit()
    counts = reindex_all(session, FakeEmbedder())
    session.commit()
    assert counts["briefings_indexed"] == 2
    assert counts["chunks_written"] >= 2


# ---- API ------------------------------------------------------------------

@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path/'rag_api.db'}"
    engine = db.reset_engine_for_tests(url)
    Base.metadata.create_all(engine)

    app.dependency_overrides[get_commentator] = lambda: FakeCommentator()
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_answerer] = lambda: FakeAnswerer()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_run_indexes_then_ask(client):
    run_date = "2026-01-06"
    # Seed market data so the summary has content to embed.
    from core.pipeline import run
    from tests.conftest import FakeProvider

    session = db.get_session_factory()()
    run(session, run_date=dt.date(2026, 1, 6), provider=FakeProvider())
    session.commit()
    session.close()

    resp = client.post(f"/briefings/run?run_date={run_date}")
    assert resp.status_code == 200

    ask = client.post("/ask", json={"question": "What happened with semiconductors?"})
    assert ask.status_code == 200
    body = ask.json()
    assert body["sources"]
    assert body["sources"][0]["run_date"] == run_date


def test_ask_rejects_empty_question(client):
    resp = client.post("/ask", json={"question": "   "})
    assert resp.status_code == 422


def test_reindex_endpoint(client):
    from core.pipeline import run
    from tests.conftest import FakeProvider

    session = db.get_session_factory()()
    run(session, run_date=dt.date(2026, 1, 6), provider=FakeProvider())
    session.commit()
    session.close()

    client.post("/briefings/run?run_date=2026-01-06")
    resp = client.post("/rag/reindex")
    assert resp.status_code == 200
    assert resp.json()["briefings_indexed"] >= 1
