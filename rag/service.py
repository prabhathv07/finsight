"""Orchestrate retrieval-augmented answering and corpus backfill.

answer_question is the one entry point the API needs: embed the question,
retrieve the most relevant past chunks, hand them to the answerer, and return
the answer together with the sources it drew on. reindex_all rebuilds the
chunk corpus from the existing briefings table, which is how you bootstrap the
index over briefings that were written before RAG existed.
"""

from sqlalchemy import select

from core.models import Briefing
from rag.answer import build_context
from rag.store import index_briefing, retrieve


def _no_context_answer(question):
    return (
        "There are no indexed briefings to answer from yet. Once briefings "
        "have been generated and indexed, ask again."
    )


def answer_question(session, question, embedder, answerer, top_k=5):
    """Return {answer, sources} for a question over the briefing corpus."""
    query_vec = embedder([question])[0]
    results = retrieve(session, query_vec, top_k=top_k)

    if not results:
        return {"question": question, "answer": _no_context_answer(question), "sources": []}

    context = build_context(results)
    answer = answerer(question, context)

    sources = [
        {
            "run_date": chunk.run_date.isoformat(),
            "source": chunk.source,
            "chunk_index": chunk.chunk_index,
            "score": round(float(score), 4),
            "excerpt": (chunk.content[:240] + "...")
            if len(chunk.content) > 240
            else chunk.content,
        }
        for chunk, score in results
    ]
    return {"question": question, "answer": answer, "sources": sources}


def reindex_all(session, embedder):
    """(Re)build chunks for every briefing. Returns counts."""
    briefings = session.scalars(select(Briefing).order_by(Briefing.run_date)).all()
    briefings_indexed = 0
    chunks_written = 0
    for briefing in briefings:
        rows = index_briefing(session, briefing, embedder)
        if rows:
            briefings_indexed += 1
            chunks_written += len(rows)
    return {"briefings_indexed": briefings_indexed, "chunks_written": chunks_written}
