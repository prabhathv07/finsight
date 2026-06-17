import pytest

from core import db
from core.models import Base
from ingestion.providers.base import Quote


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path/'test.db'}"
    engine = db.reset_engine_for_tests(url)
    Base.metadata.create_all(engine)
    factory = db.get_session_factory()
    s = factory()
    try:
        yield s
    finally:
        s.close()


class FakeProvider:
    """Deterministic stand-in for yfinance so tests need no network."""

    name = "fake"

    def __init__(self):
        self._prices = {}

    def quotes(self, symbols):
        out = []
        for i, symbol in enumerate(symbols):
            out.append(
                Quote(
                    symbol=symbol,
                    price=100.0 + i,
                    change=1.0,
                    change_pct=float(i),
                    volume=1000.0 + i,
                )
            )
        return out

    def history(self, symbol, days=60):
        return [float(x) for x in range(1, days + 1)]


@pytest.fixture
def fake_provider():
    return FakeProvider()
