"""Polygon.io REST provider.

Covers US equities, ETFs, and crypto. Silently skips symbols Polygon
cannot serve (futures with =F suffix, indices with ^ prefix, forex like
DX-Y.NYB) so those symbols fall through to the yfinance fallback that
wraps this provider in production.

Uses only stdlib urllib so no extra dependency is needed.
"""

import datetime as dt
import json
import urllib.error
import urllib.request

from ingestion.providers.base import Quote

_BASE = "https://api.polygon.io"


def _polygon_ticker(symbol):
    """Convert a yfinance-style symbol to the Polygon ticker.

    Returns None for symbols Polygon cannot serve.
    """
    if symbol.startswith("^"):
        return None  # indices: ^VIX, ^TNX
    if symbol.endswith("=F"):
        return None  # futures: ES=F, NQ=F, GC=F, CL=F
    if symbol.endswith(".NYB"):
        return None  # DX-Y.NYB (DXY)
    if symbol.endswith("-USD"):
        # Crypto: BTC-USD -> X:BTCUSD
        base = symbol[:-4]
        return f"X:{base}USD"
    return symbol.upper()


class PolygonProvider:
    name = "polygon"

    def __init__(self, api_key):
        self.api_key = api_key

    def _get(self, path, params=None):
        params = dict(params or {})
        params["apiKey"] = self.api_key
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{_BASE}{path}?{qs}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def quotes(self, symbols):
        out = []
        for symbol in symbols:
            ticker = _polygon_ticker(symbol)
            if ticker is None:
                continue
            quote = self._one_quote(symbol, ticker)
            if quote is not None:
                out.append(quote)
        return out

    def _one_quote(self, symbol, ticker):
        data = self._get(f"/v2/aggs/ticker/{ticker}/prev")
        if not data or not data.get("results"):
            return None
        bar = data["results"][0]
        close = bar.get("c")
        open_ = bar.get("o")
        volume = bar.get("v")
        if close is None:
            return None
        change = (close - open_) if open_ is not None else None
        change_pct = (change / open_ * 100.0) if (open_ and change is not None) else None
        return Quote(
            symbol=symbol,
            price=close,
            change=change,
            change_pct=change_pct,
            volume=volume,
        )

    def history(self, symbol, days=60):
        ticker = _polygon_ticker(symbol)
        if ticker is None:
            return []
        end = dt.date.today()
        # Fetch extra calendar days to ensure we get the requested trading days.
        start = end - dt.timedelta(days=days + 40)
        data = self._get(
            f"/v2/aggs/ticker/{ticker}/range/1/day/{start.isoformat()}/{end.isoformat()}",
            params={"adjusted": "true", "sort": "asc", "limit": str(days + 40)},
        )
        if not data or not data.get("results"):
            return []
        prices = [bar["c"] for bar in data["results"] if "c" in bar]
        return prices[-days:] if len(prices) > days else prices
