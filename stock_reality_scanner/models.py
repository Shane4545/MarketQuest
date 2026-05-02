from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class DailyQuote:
    symbol: str
    day: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    adjusted_close: float | None
    volume: int | None
    source: str


@dataclass(frozen=True)
class HindsightMove:
    symbol: str
    entry_day: date
    exit_day: date
    entry_close: float
    exit_close: float
    return_pct: float
    source: str


@dataclass(frozen=True)
class HindsightOptimizerResult:
    """Best real outcome over a completed period (knowing history); includes gap to an optional target."""

    symbol: str
    entry_day: date
    exit_day: date
    entry_price: float
    exit_price: float
    return_pct: float
    return_multiple: float
    starting_cash: float
    ending_cash: float
    target_cash: float
    required_multiple: float
    achieved_multiple: float
    target_achieved: bool
    distance_from_target: float
    source: str
    fetched_at: datetime
    universe_limited_warning: str | None = None


@dataclass(frozen=True)
class StrategySignal:
    signal_day: date
    symbol: str
    score: float
    reason: str


@dataclass(frozen=True)
class PaperTrade:
    signal_day: date
    entry_day: date
    exit_day: date
    symbol: str
    entry_price: float
    exit_price: float
    shares: float
    starting_cash: float
    ending_cash: float
    return_pct: float


@dataclass(frozen=True)
class BacktestSummary:
    starting_cash: float
    ending_cash: float
    return_pct: float
    trade_count: int
    max_drawdown_pct: float
    generated_at: datetime
    mode: str
