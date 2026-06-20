"""Write and read briefing chunks.

Indexing is idempotent per briefing: re-indexing a day replaces its chunks
rather than duplicating them, which mirrors how the briefings table is keyed
on run_date. Retrieval is dialect-aware -- pgvector's indexed cosine distance
on Postgres, a plain Python cosine scan on SQLite -- so the same call works in
production and in the offline test suite.
"""

import datetime as dt

from sqlalchemy import delete, select

from core.models import BriefingChunk
from rag.chunk import chunk_briefing
from rag.embed import cosine_similarity


def index_briefing(session, briefing, embedder, model_name=None):
    """Chunk, embed, and store one briefing. Returns the chunks written."""
    pieces = chunk_briefing(briefing.summary_input, briefing.llm_output)
    if not pieces:
        return []

    vectors = embedder([text for _, text in pieces])
    model_name = model_name or getattr(embedder, "model", getattr(embedder, "name", "unknown"))

    # Replace any existing chunks for this briefing so re-runs stay clean.
    session.execute(
        delete(BriefingChunk).where(BriefingChunk.briefing_id == briefing.id)
    )

    now = dt.datetime.now(dt.UTC)
    rows = []
    for i, ((source, text), vector) in enumerate(zip(pieces, vectors)):
        row = BriefingChunk(
            briefing_id=briefing.id,
            run_date=briefing.run_date,
            chunk_index=i,
            source=source,
            content=text,
            embedding=list(vector),
            embed_model=model_name,
            created_at=now,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return rows


def _retrieve_postgres(session, query_embedding, top_k):
    distance = BriefingChunk.embedding.cosine_distance(query_embedding)
    rows = session.execute(
        select(BriefingChunk, distance.label("distance"))
        .where(BriefingChunk.embedding.isnot(None))
        .order_by(distance)
        .limit(top_k)
    ).all()
    # Cosine similarity = 1 - cosine distance.
    return [(chunk, 1.0 - float(dist)) for chunk, dist in rows]


def _retrieve_python(session, query_embedding, top_k):
    chunks = session.scalars(
        select(BriefingChunk).where(BriefingChunk.embedding.isnot(None))
    ).all()
    scored = [
        (chunk, cosine_similarity(query_embedding, chunk.embedding))
        for chunk in chunks
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


def retrieve(session, query_embedding, top_k=5):
    """Return the top_k (chunk, similarity) pairs for a query vector."""
    if session.bind.dialect.name == "postgresql":
        return _retrieve_postgres(session, query_embedding, top_k)
    return _retrieve_python(session, query_embedding, top_k)
