import datetime as dt

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RawQuote(Base):
    """One symbol's snapshot from a single morning pull.

    Category separates the parts of the briefing (futures, macro, sector,
    mover, watchlist) so each section can be queried on its own. Anything
    that does not fit the common columns (short interest, options flow)
    goes in extra as JSON rather than widening the table.
    """

    __tablename__ = "raw_quotes"
    __table_args__ = (
        UniqueConstraint("run_date", "category", "symbol", name="uq_quote_run_symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_date: Mapped[dt.date] = mapped_column(Date, index=True)
    captured_at: Mapped[dt.datetime] = mapped_column(DateTime)
    category: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    price: Mapped[float] = mapped_column(Float, nullable=True)
    change: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[float] = mapped_column(Float, nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)


class Indicator(Base):
    """Technical indicators computed from a symbol's recent history."""

    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint("run_date", "symbol", name="uq_indicator_run_symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_date: Mapped[dt.date] = mapped_column(Date, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime)
    rsi: Mapped[float] = mapped_column(Float, nullable=True)
    ma9: Mapped[float] = mapped_column(Float, nullable=True)
    ma20: Mapped[float] = mapped_column(Float, nullable=True)
    ma50: Mapped[float] = mapped_column(Float, nullable=True)
    sparkline: Mapped[str] = mapped_column(String(64), nullable=True)


class Briefing(Base):
    """One LLM analysis run, logged in full.

    Storing the exact input, the raw output, the model name, the latency,
    and the status for every call is the monitoring story: it is how you
    spot a model regression, a latency spike, or a run that fell back to
    the template after the model errored.
    """

    __tablename__ = "briefings"
    __table_args__ = (
        UniqueConstraint("run_date", name="uq_briefing_run_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_date: Mapped[dt.date] = mapped_column(Date, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    model_name: Mapped[str] = mapped_column(String(64))
    summary_input: Mapped[str] = mapped_column(Text)
    llm_output: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str] = mapped_column(Text, nullable=True)


class Subscriber(Base):
    """A mailing-list subscriber.

    Double opt-in: a new row starts pending with a confirm token and only
    receives briefings once status is confirmed. Every row also carries an
    unsubscribe token so the link in each email resolves to one person.
    """

    __tablename__ = "subscribers"
    __table_args__ = (
        UniqueConstraint("email", name="uq_subscriber_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    confirm_token: Mapped[str] = mapped_column(String(64), index=True)
    unsubscribe_token: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    confirmed_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=True)


def create_all():
    from core.db import get_engine

    Base.metadata.create_all(get_engine())
