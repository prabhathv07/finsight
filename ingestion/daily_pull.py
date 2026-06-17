"""The morning pull.

Walks each section of the universe, fetches quotes through whatever
provider is passed in, and tags every result with its category so the
persistence layer can store it and the briefing can group it.
"""

from ingestion import universe


def _default_provider():
    from ingestion.providers.yfinance_provider import YFinanceProvider

    return YFinanceProvider()

SECTION_SYMBOLS = {
    "futures": universe.FUTURES,
    "macro": universe.MACRO,
    "sector": universe.SECTORS,
    "mover": universe.MOVER_UNIVERSE,
    "watchlist": universe.WATCHLIST,
}


def pull(provider=None):
    """Return a list of (category, Quote) for the day."""
    provider = provider or _default_provider()
    results = []
    for category, symbols in SECTION_SYMBOLS.items():
        for quote in provider.quotes(symbols):
            results.append((category, quote))
    return results


def history_for(symbols, provider=None, days=60):
    """Closing-price history per symbol, for indicator math."""
    provider = provider or _default_provider()
    return {symbol: provider.history(symbol, days) for symbol in symbols}
