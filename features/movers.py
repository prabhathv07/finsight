"""Pick the day's biggest movers from a list of quote records.

A quote here is any object with a change_pct attribute or key. Both shapes
turn up in the pipeline (ORM rows and plain dicts during ingestion), so we
accept either.
"""


def _pct(quote):
    if isinstance(quote, dict):
        return quote.get("change_pct")
    return getattr(quote, "change_pct", None)


def top_gainers(quotes, n=5):
    ranked = [q for q in quotes if _pct(q) is not None]
    ranked.sort(key=_pct, reverse=True)
    return ranked[:n]


def top_losers(quotes, n=5):
    ranked = [q for q in quotes if _pct(q) is not None]
    ranked.sort(key=_pct)
    return ranked[:n]
