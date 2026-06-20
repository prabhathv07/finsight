"""Retrieval quality evaluation for the RAG layer.

Run after indexing at least a few briefings:

    python eval_rag.py

Prints per-question retrieval scores, the score distribution, hit@5, and MRR.
Use the distribution to decide whether MIN_RETRIEVAL_SCORE in rag/service.py
needs adjusting — don't guess the threshold, read it from your own data.

Each entry in EVAL_SET is:
    question      — what a user would ask
    expected_dates — one or more briefing run_dates that should appear in top-5
"""

import os
import sys

EVAL_SET = [
    {
        "question": "Which sectors were leading pre-market?",
        "expected_dates": [],   # fill in after you have real briefings indexed
    },
    {
        "question": "How did semiconductors perform?",
        "expected_dates": [],
    },
    {
        "question": "What was the VIX doing?",
        "expected_dates": [],
    },
    {
        "question": "Which stocks were top gainers?",
        "expected_dates": [],
    },
    {
        "question": "What were the futures saying about the open?",
        "expected_dates": [],
    },
    {
        "question": "How was NVDA trending?",
        "expected_dates": [],
    },
    {
        "question": "Was gold up or down?",
        "expected_dates": [],
    },
    {
        "question": "What were the main risks flagged?",
        "expected_dates": [],
    },
    {
        "question": "How did energy stocks do?",
        "expected_dates": [],
    },
    {
        "question": "What was the RSI on MSFT?",
        "expected_dates": [],
    },
]


def main():
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./demo.db")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    embed_model = os.environ.get("EMBED_MODEL", "text-embedding-004")

    from core.db import reset_engine_for_tests, get_session_factory
    from core.models import Base
    from core.db import get_engine

    if "sqlite" in db_url:
        reset_engine_for_tests(db_url)
    Base.metadata.create_all(get_engine())
    session = get_session_factory()()

    from rag.embed import GeminiEmbedder
    from rag.store import retrieve

    if not api_key:
        print("GEMINI_API_KEY not set — cannot embed. Set it and re-run.")
        sys.exit(1)

    embedder = GeminiEmbedder(api_key=api_key, model=embed_model)

    all_scores = []
    hits = 0
    rr_sum = 0.0
    rows = []

    print(f"\n{'Question':<45} {'Top score':>10}  {'Hit@5':>6}  Scores")
    print("-" * 90)

    for entry in EVAL_SET:
        q = entry["question"]
        expected = set(entry["expected_dates"])

        try:
            vec = embedder([q])[0]
        except Exception as e:
            print(f"  embed failed: {e}")
            continue

        results = retrieve(session, vec, top_k=5)
        scores = [round(float(s), 4) for _, s in results]
        dates = [chunk.run_date.isoformat() for chunk, _ in results]
        all_scores.extend(scores)

        hit = any(d in expected for d in dates) if expected else None
        if hit:
            hits += 1
            rank = next(i + 1 for i, d in enumerate(dates) if d in expected)
            rr_sum += 1.0 / rank

        hit_str = ("✅" if hit else "❌") if expected else "—"
        top = scores[0] if scores else 0.0
        rows.append((q, top, hit_str, scores))
        print(f"  {q:<43} {top:>10.4f}  {hit_str:>6}  {scores}")

    print("\n--- Score distribution ---")
    if all_scores:
        all_scores.sort()
        n = len(all_scores)
        print(f"  min={all_scores[0]:.4f}  "
              f"p25={all_scores[n//4]:.4f}  "
              f"median={all_scores[n//2]:.4f}  "
              f"p75={all_scores[3*n//4]:.4f}  "
              f"max={all_scores[-1]:.4f}")
        print(f"  mean={sum(all_scores)/n:.4f}")

    evaluated = [r for r in rows if r[2] != "—"]
    if evaluated:
        hit5 = hits / len(evaluated)
        mrr = rr_sum / len(evaluated)
        print(f"\n  hit@5 = {hit5:.2f}   MRR = {mrr:.2f}  (over {len(evaluated)} labelled questions)")
        print("\nTo improve: fill in expected_dates in EVAL_SET using real briefing dates,")
        print("then use the median/p25 score to calibrate MIN_RETRIEVAL_SCORE in rag/service.py.")
    else:
        print("\n  No expected_dates filled in yet — score distribution above tells you")
        print("  where good vs weak retrieval splits. Set MIN_RETRIEVAL_SCORE just above")
        print("  the gap between relevant and irrelevant scores.")


if __name__ == "__main__":
    main()
