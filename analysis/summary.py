"""Turn a day's stored data into the compact text the model reads.

The original script learned the hard way that dumping raw JSON at the model
truncates the response and breaks parsing. This keeps the input small and
readable: one line per symbol, indicators folded in where we have them.
"""

from sqlalchemy import select

from core.models import Indicator, RawQuote
from features.movers import top_gainers, top_losers

SECTION_ORDER = ["futures", "macro", "sector", "watchlist"]
SECTION_TITLES = {
    "futures": "FUTURES",
    "macro": "MACRO",
    "sector": "SECTORS",
    "watchlist": "WATCHLIST",
}


def _fmt_quote(quote, indicator=None):
    parts = [quote.symbol]
    if quote.price is not None:
        parts.append(f"{quote.price:.2f}")
    if quote.change_pct is not None:
        parts.append(f"({quote.change_pct:+.2f}%)")
    if indicator is not None:
        if indicator.rsi is not None:
            parts.append(f"RSI {indicator.rsi:.1f}")
        if indicator.ma20 is not None:
            parts.append(f"MA20 {indicator.ma20:.2f}")
    return " ".join(parts)


def build_summary(session, run_date):
    quotes = session.scalars(
        select(RawQuote).where(RawQuote.run_date == run_date)
    ).all()
    indicators = session.scalars(
        select(Indicator).where(Indicator.run_date == run_date)
    ).all()
    indicator_by_symbol = {i.symbol: i for i in indicators}

    by_category = {}
    for q in quotes:
        by_category.setdefault(q.category, []).append(q)

    lines = [f"Pre-market summary for {run_date.isoformat()}", ""]

    for category in SECTION_ORDER:
        rows = by_category.get(category)
        if not rows:
            continue
        lines.append(SECTION_TITLES[category])
        for q in sorted(rows, key=lambda x: x.symbol):
            lines.append(_fmt_quote(q, indicator_by_symbol.get(q.symbol)))
        lines.append("")

    movers = by_category.get("mover", [])
    if movers:
        lines.append("TOP GAINERS")
        for q in top_gainers(movers):
            lines.append(_fmt_quote(q))
        lines.append("")
        lines.append("TOP LOSERS")
        for q in top_losers(movers):
            lines.append(_fmt_quote(q))
        lines.append("")

    return "\n".join(lines).strip()
