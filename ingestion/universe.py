"""The symbols pulled each morning, grouped by briefing section.

Edit here in one place to change what the briefing covers.
"""

# Index futures — the four major US contracts
FUTURES = ["ES=F", "NQ=F", "YM=F", "RTY=F"]

# Macro backdrop: volatility, gold, oil, crypto, rates, dollar
MACRO = ["^VIX", "GC=F", "CL=F", "BTC-USD", "ETH-USD", "^TNX", "^TYX", "DX-Y.NYB"]

# Sector ETFs — broad coverage across all 11 GICS sectors
SECTORS = [
    "XLK",   # Technology
    "SOXX",  # Semiconductors
    "XLC",   # Communication Services
    "XLY",   # Consumer Discretionary
    "XLP",   # Consumer Staples
    "XLF",   # Financials
    "XLV",   # Health Care
    "XLE",   # Energy
    "XLB",   # Materials
    "XLI",   # Industrials
    "XLU",   # Utilities
    "XLRE",  # Real Estate
]

# Universe scanned for top gainers and losers each morning.
# Covers mega-cap and large-cap names across tech, finance, energy,
# health care, and consumer — the stocks that move the tape.
MOVER_UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA",
    # Semiconductors
    "AMD", "AVGO", "QCOM", "TXN", "INTC", "MU", "AMAT", "LRCX", "KLAC",
    # Software / cloud
    "CRM", "ORCL", "ADBE", "NOW", "SNDK", "PANW", "CRWD", "NET",
    # Large-cap tech / hardware
    "AAPL", "DELL", "HPE", "ANET",
    # Financials
    "JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "V", "MA", "AXP", "SCHW",
    # Energy
    "XOM", "CVX", "COP", "SLB", "OXY", "EOG",
    # Health care
    "UNH", "JNJ", "PFE", "MRK", "ABBV", "LLY", "TMO", "ABT",
    # Consumer
    "WMT", "COST", "AMZN", "HD", "NKE", "MCD", "SBUX",
    # Industrials / defense
    "BA", "CAT", "GE", "RTX", "LMT", "HON", "UPS", "FDX",
    # ETFs that move on sentiment
    "SPY", "QQQ", "IWM", "ARK",
]
# Deduplicate while preserving order
_seen_movers: list = []
for _s in MOVER_UNIVERSE:
    if _s not in _seen_movers:
        _seen_movers.append(_s)
MOVER_UNIVERSE = _seen_movers

# Watchlist — high-conviction names tracked with full indicator detail
WATCHLIST = [
    "NVDA",  # AI infrastructure bellwether
    "MSFT",  # Azure + OpenAI proxy
    "META",  # Ad market + Llama
    "GOOGL", # Search + Gemini
    "AMZN",  # AWS + consumer
    "TSLA",  # EV + energy + Optimus
    "AAPL",  # Consumer cycle
    "AMD",   # Datacenter GPU competition
    "AVGO",  # Custom AI silicon
    "JPM",   # Financial system health
]


def all_symbols():
    seen = []
    for group in (FUTURES, MACRO, SECTORS, MOVER_UNIVERSE, WATCHLIST):
        for s in group:
            if s not in seen:
                seen.append(s)
    return seen
