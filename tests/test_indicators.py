from features.indicators import (
    indicator_set,
    relative_strength_index,
    simple_moving_average,
)


def test_sma_basic():
    assert simple_moving_average([1, 2, 3, 4, 5], 5) == 3.0
    assert simple_moving_average([2, 4, 6], 2) == 5.0


def test_sma_needs_enough_history():
    assert simple_moving_average([1, 2], 5) is None


def test_rsi_all_gains_is_100():
    prices = list(range(1, 30))
    assert relative_strength_index(prices) == 100.0


def test_rsi_all_losses_is_0():
    prices = list(range(30, 1, -1))
    assert relative_strength_index(prices) == 0.0


def test_rsi_stays_in_range():
    prices = [10, 11, 10.5, 12, 11.8, 13, 12.5, 14, 13.2, 15,
              14.1, 16, 15.3, 17, 16.2, 18]
    value = relative_strength_index(prices)
    assert value is not None
    assert 0.0 <= value <= 100.0


def test_rsi_needs_enough_history():
    assert relative_strength_index([1, 2, 3], period=14) is None


def test_indicator_set_keys():
    prices = [float(x) for x in range(1, 60)]
    values = indicator_set(prices)
    assert set(values) == {"rsi", "ma9", "ma20", "ma50"}
    assert values["ma9"] is not None
