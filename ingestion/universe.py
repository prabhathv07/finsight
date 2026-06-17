"""The symbols pulled each morning, grouped by briefing section.

Futures, macro, and sector lists match the v2 email build. The mover
universe and watchlist are the two lists to reconcile against the
current script, since those were tuned by hand over time. Edit here in
one place rather than scattering tickers through the code.
"""

FUTURES = ["ES=F", "NQ=F", "YM=F", "RTY=F"]

MACRO = ["^VIX", "GC=F", "CL=F", "BTC-USD", "^TNX", "DX-Y.NYB"]

SECTORS = ["XLK", "SOXX", "XLF", "XLE", "XLV", "XLY", "XLU", "XLI"]

# Universe scanned for top gainers and losers. Reconcile against the
# 40-symbol list in the current script before the first real run.
MOVER_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD",
    "NFLX", "INTC", "CRM", "ORCL", "ADBE", "AVGO", "QCOM", "TXN",
    "JPM", "BAC", "GS", "MS", "WFC", "C", "V", "MA",
    "XOM", "CVX", "COP", "SLB", "UNH", "JNJ", "PFE", "MRK",
    "WMT", "COST", "HD", "NKE", "DIS", "BA", "CAT", "GE",
]

# Per-symbol deep dive with options flow. Reconcile against the current
# watchlist before the first real run.
WATCHLIST = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "META", "AMZN", "GOOGL"]


def all_symbols():
    seen = []
    for group in (FUTURES, MACRO, SECTORS, MOVER_UNIVERSE, WATCHLIST):
        for s in group:
            if s not in seen:
                seen.append(s)
    return seen
