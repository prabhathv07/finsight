"""Provider contract.

Every data source returns the same Quote shape so the pipeline does not
care where a number came from. Adding Polygon later means writing one
class that returns Quote objects, not touching the pipeline.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Quote:
    symbol: str
    price: float | None = None
    change: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    extra: dict = field(default_factory=dict)


class MarketDataProvider(Protocol):
    name: str

    def quotes(self, symbols: list[str]) -> list[Quote]:
        ...

    def history(self, symbol: str, days: int) -> list[float]:
        """Closing prices, oldest first, for indicator math."""
        ...
