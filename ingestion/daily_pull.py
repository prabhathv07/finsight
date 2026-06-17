"""The morning pull.

Walks each section of the universe, fetches quotes through whatever
provider is passed in, and tags every result with its category so the
persistence layer can store it and the briefing can group it.
"""

from ingestion import universe


class FallbackProvider:
    """Try the primary provider first; fall back per-symbol to the secondary.

    Polygon covers equities and skips futures/indices/forex. yfinance covers
    everything but is unofficial. Combining them gives Polygon's data quality
    for equities and yfinance's breadth for the symbols Polygon cannot serve.
    """

    def __init__(self, primary, secondary):
        self.primary = primary
        self.secondary = secondary
        self.name = f"{primary.name}+{secondary.name}"

    def quotes(self, symbols):
        primary_map = {q.symbol: q for q in self.primary.quotes(symbols)}
        missing = [s for s in symbols if s not in primary_map]
        if missing:
            for q in self.secondary.quotes(missing):
                primary_map[q.symbol] = q
        return list(primary_map.values())

    def history(self, symbol, days=60):
        result = self.primary.history(symbol, days)
        if not result:
            return self.secondary.history(symbol, days)
        return result


def _default_provider():
    from ingestion.providers.yfinance_provider import YFinanceProvider

    yf = YFinanceProvider()

    from core.config import get_settings

    if get_settings().has_polygon():
        from ingestion.providers.polygon_provider import PolygonProvider

        return FallbackProvider(
            primary=PolygonProvider(get_settings().polygon_api_key),
            secondary=yf,
        )

    return yf

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
