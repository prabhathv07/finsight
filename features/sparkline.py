"""ASCII sparklines.

The email build settled on block characters instead of SVG because Gmail
strips inline SVG. These same strings render fine in the dashboard too,
so the logic lives here once.
"""

BLOCKS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


def sparkline(prices):
    if not prices:
        return ""
    low = min(prices)
    high = max(prices)
    if high == low:
        # Flat series: render a mid-height bar rather than dividing by zero.
        return BLOCKS[len(BLOCKS) // 2] * len(prices)

    span = high - low
    out = []
    for p in prices:
        idx = round((p - low) / span * (len(BLOCKS) - 1))
        out.append(BLOCKS[idx])
    return "".join(out)
