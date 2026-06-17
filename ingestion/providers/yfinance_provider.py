"""yfinance provider.

yfinance is an unofficial client and the shape of what it returns shifts
between versions, so everything funnels through normalize helpers and any
single bad symbol is skipped rather than killing the whole pull.
"""

from ingestion.providers.base import Quote


def _yf():
    # Imported on first use so the rest of the system does not depend on
    # yfinance being installed when a different provider is in play.
    import yfinance as yf

    return yf


class YFinanceProvider:
    name = "yfinance"

    def quotes(self, symbols):
        out = []
        for symbol in symbols:
            quote = self._one_quote(symbol)
            if quote is not None:
                out.append(quote)
        return out

    def _one_quote(self, symbol):
        try:
            ticker = _yf().Ticker(symbol)
            frame = ticker.history(period="2d")
            if frame.empty:
                return None

            last = float(frame["Close"].iloc[-1])
            prev = float(frame["Close"].iloc[-2]) if len(frame) > 1 else last
            change = last - prev
            change_pct = (change / prev * 100.0) if prev else None
            volume = float(frame["Volume"].iloc[-1]) if "Volume" in frame else None

            return Quote(
                symbol=symbol,
                price=last,
                change=change,
                change_pct=change_pct,
                volume=volume,
            )
        except Exception:
            # A dead symbol should not take down the morning run.
            return None

    def history(self, symbol, days=60):
        try:
            frame = _yf().Ticker(symbol).history(period=f"{days}d")
            if frame.empty:
                return []
            return [float(x) for x in frame["Close"].tolist()]
        except Exception:
            return []
