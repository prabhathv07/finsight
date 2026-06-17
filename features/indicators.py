"""Technical indicators computed from a price series.

Inputs are plain lists of closing prices, oldest first. Keeping these as
pure functions means they can be tested without a network or a database,
and reused by both the daily pipeline and any backfill script.
"""


def simple_moving_average(prices, window):
    if window <= 0:
        raise ValueError("window must be positive")
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / window


def relative_strength_index(prices, period=14):
    """Wilder-style RSI over the given period.

    Returns None when there is not enough history. A series that only
    rises returns 100, one that only falls returns 0.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if len(prices) < period + 1:
        return None

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    window = deltas[-period:]

    gains = [d for d in window if d > 0]
    losses = [-d for d in window if d < 0]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def indicator_set(prices):
    """Bundle the indicators we store per symbol."""
    return {
        "rsi": relative_strength_index(prices),
        "ma9": simple_moving_average(prices, 9),
        "ma20": simple_moving_average(prices, 20),
        "ma50": simple_moving_average(prices, 50),
    }
