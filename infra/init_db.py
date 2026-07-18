"""Create database tables. Safe to run repeatedly.

On Postgres this also enables the pgvector extension (needed before the
briefing_chunks embedding column can be created) and builds an IVFFlat
cosine index for fast nearest-neighbour retrieval. Both steps are skipped
on SQLite, which the test suite uses.
"""

from sqlalchemy import text

from core.db import get_engine
from core.models import create_all


def _enable_pgvector(engine):
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def _create_vector_index(engine):
    # Wrapped in try/except so a version mismatch never crashes the briefing run.
    if engine.dialect.name != "postgresql":
        return
    from core.config import get_settings

    if get_settings().embed_dim > 2000:
        # pgvector caps both ivfflat and hnsw indexes at 2000 dimensions, so
        # the 3072-dim gemini-embedding-001 column cannot be indexed at all.
        # Retrieval falls back to an exact scan, which is fine at this corpus
        # size; skip quietly instead of warning on every run.
        return
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_briefing_chunks_embedding "
                    "ON briefing_chunks USING hnsw (embedding vector_cosine_ops) "
                    "WITH (m = 16, ef_construction = 64)"
                )
            )
    except Exception as exc:
        print(f"warning: could not create vector index (search will use exact scan): {exc}")


def init():
    engine = get_engine()
    _enable_pgvector(engine)  # must run before create_all builds the vector column
    create_all()
    _create_vector_index(engine)


if __name__ == "__main__":
    init()
    print("tables ready")
