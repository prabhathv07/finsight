from features.movers import top_gainers, top_losers
from features.sparkline import BLOCKS, sparkline


def test_sparkline_length_matches_input():
    assert len(sparkline([1, 2, 3, 4, 5])) == 5


def test_sparkline_flat_series():
    out = sparkline([5, 5, 5])
    assert out == BLOCKS[len(BLOCKS) // 2] * 3


def test_sparkline_endpoints():
    out = sparkline([1, 5, 10])
    assert out[0] == BLOCKS[0]
    assert out[-1] == BLOCKS[-1]


def test_sparkline_empty():
    assert sparkline([]) == ""


def test_top_gainers_orders_by_pct():
    quotes = [
        {"symbol": "A", "change_pct": 1.0},
        {"symbol": "B", "change_pct": 5.0},
        {"symbol": "C", "change_pct": -2.0},
    ]
    result = top_gainers(quotes, n=2)
    assert [q["symbol"] for q in result] == ["B", "A"]


def test_top_losers_orders_by_pct():
    quotes = [
        {"symbol": "A", "change_pct": 1.0},
        {"symbol": "B", "change_pct": 5.0},
        {"symbol": "C", "change_pct": -2.0},
    ]
    result = top_losers(quotes, n=1)
    assert result[0]["symbol"] == "C"


def test_movers_skip_missing_pct():
    quotes = [{"symbol": "A", "change_pct": None}, {"symbol": "B", "change_pct": 3.0}]
    assert [q["symbol"] for q in top_gainers(quotes)] == ["B"]
