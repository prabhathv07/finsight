"""Tests for the Polygon provider and the FallbackProvider.

The Polygon tests use a patched urllib so no network is needed. The
FallbackProvider tests use simple stub providers and verify the routing
logic.
"""

import json
from unittest.mock import MagicMock, patch


from ingestion.daily_pull import FallbackProvider
from ingestion.providers.base import Quote
from ingestion.providers.polygon_provider import PolygonProvider, _polygon_ticker


# ── ticker normalization ──────────────────────────────────────────────────────

def test_polygon_ticker_equity():
    assert _polygon_ticker("AAPL") == "AAPL"
    assert _polygon_ticker("aapl") == "AAPL"


def test_polygon_ticker_crypto():
    assert _polygon_ticker("BTC-USD") == "X:BTCUSD"


def test_polygon_ticker_skips_futures():
    assert _polygon_ticker("ES=F") is None
    assert _polygon_ticker("GC=F") is None
    assert _polygon_ticker("CL=F") is None


def test_polygon_ticker_skips_indices():
    assert _polygon_ticker("^VIX") is None
    assert _polygon_ticker("^TNX") is None


def test_polygon_ticker_skips_forex():
    assert _polygon_ticker("DX-Y.NYB") is None


# ── PolygonProvider.quotes ────────────────────────────────────────────────────

def _mock_urlopen(payload):
    """Return a context-manager mock that yields the given payload as JSON."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=MagicMock(read=lambda: json.dumps(payload).encode()))
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _prev_bar(close=150.0, open_=148.0, volume=1_000_000):
    return {"status": "OK", "results": [{"c": close, "o": open_, "v": volume}]}


def test_polygon_quotes_returns_equity():
    provider = PolygonProvider("test-key")
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_prev_bar(close=200.0, open_=198.0))):
        quotes = provider.quotes(["MSFT"])
    assert len(quotes) == 1
    q = quotes[0]
    assert q.symbol == "MSFT"
    assert q.price == 200.0
    assert abs(q.change - 2.0) < 0.001
    assert abs(q.change_pct - (2.0 / 198.0 * 100)) < 0.001


def test_polygon_quotes_skips_unsupported():
    provider = PolygonProvider("test-key")
    # None of these should make a network call; provider skips them silently.
    with patch("urllib.request.urlopen") as mock_open:
        quotes = provider.quotes(["ES=F", "^VIX", "DX-Y.NYB"])
    mock_open.assert_not_called()
    assert quotes == []


def test_polygon_quotes_handles_api_error():
    provider = PolygonProvider("test-key")
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        quotes = provider.quotes(["AAPL"])
    assert quotes == []


def test_polygon_quotes_handles_empty_results():
    provider = PolygonProvider("test-key")
    empty = {"status": "OK", "results": []}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(empty)):
        quotes = provider.quotes(["AAPL"])
    assert quotes == []


# ── PolygonProvider.history ───────────────────────────────────────────────────

def test_polygon_history_returns_closes():
    provider = PolygonProvider("test-key")
    bars = {"status": "OK", "results": [{"c": float(i)} for i in range(1, 61)]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(bars)):
        prices = provider.history("AAPL", days=60)
    assert len(prices) == 60
    assert prices[-1] == 60.0


def test_polygon_history_skips_unsupported():
    provider = PolygonProvider("test-key")
    with patch("urllib.request.urlopen") as mock_open:
        result = provider.history("ES=F", days=60)
    mock_open.assert_not_called()
    assert result == []


def test_polygon_history_caps_at_requested_days():
    provider = PolygonProvider("test-key")
    # API returns more bars than requested.
    bars = {"status": "OK", "results": [{"c": float(i)} for i in range(1, 200)]}
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(bars)):
        prices = provider.history("AAPL", days=30)
    assert len(prices) == 30


# ── FallbackProvider ──────────────────────────────────────────────────────────

class _StubProvider:
    def __init__(self, name, quote_symbols, history_result=None):
        self.name = name
        self._quote_symbols = quote_symbols
        self._history_result = history_result or []

    def quotes(self, symbols):
        return [
            Quote(symbol=s, price=100.0, change_pct=1.0)
            for s in symbols
            if s in self._quote_symbols
        ]

    def history(self, symbol, days=60):
        return self._history_result if symbol in self._quote_symbols else []


def test_fallback_uses_primary():
    primary = _StubProvider("primary", {"AAPL", "MSFT"})
    secondary = _StubProvider("secondary", {"AAPL", "MSFT", "ES=F"})
    provider = FallbackProvider(primary=primary, secondary=secondary)

    quotes = provider.quotes(["AAPL", "MSFT"])
    symbols = {q.symbol for q in quotes}
    assert symbols == {"AAPL", "MSFT"}


def test_fallback_fills_missing_from_secondary():
    primary = _StubProvider("primary", {"AAPL"})
    secondary = _StubProvider("secondary", {"ES=F", "^VIX"})
    provider = FallbackProvider(primary=primary, secondary=secondary)

    quotes = provider.quotes(["AAPL", "ES=F", "^VIX"])
    symbols = {q.symbol for q in quotes}
    assert symbols == {"AAPL", "ES=F", "^VIX"}


def test_fallback_history_uses_secondary_when_primary_empty():
    primary = _StubProvider("primary", set())
    secondary = _StubProvider("secondary", {"ES=F"}, history_result=[1.0, 2.0, 3.0])
    provider = FallbackProvider(primary=primary, secondary=secondary)

    result = provider.history("ES=F", days=60)
    assert result == [1.0, 2.0, 3.0]


def test_fallback_history_prefers_primary():
    primary = _StubProvider("primary", {"AAPL"}, history_result=[10.0, 20.0])
    secondary = _StubProvider("secondary", {"AAPL"}, history_result=[1.0, 2.0])
    provider = FallbackProvider(primary=primary, secondary=secondary)

    result = provider.history("AAPL", days=60)
    assert result == [10.0, 20.0]


def test_fallback_name_combines_providers():
    primary = _StubProvider("polygon", set())
    secondary = _StubProvider("yfinance", set())
    provider = FallbackProvider(primary=primary, secondary=secondary)
    assert provider.name == "polygon+yfinance"
