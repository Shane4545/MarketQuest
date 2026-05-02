from datetime import date, datetime

from stock_reality_scanner.models import (
    BacktestSummary,
    DailyQuote,
    HindsightMove,
    HindsightOptimizerResult,
    PaperTrade,
    StrategySignal,
)
from stock_reality_scanner.settings import (
    DEFAULT_STARTING_CASH,
    DEFAULT_TARGET_CASH,
    REQUIRED_MULTIPLE_TO_DEFAULT_TARGET,
)


def test_daily_quote_model():
    quote = DailyQuote(
        symbol="AAPL",
        day=date(2026, 1, 2),
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.0,
        adjusted_close=104.0,
        volume=1000,
        source="test",
    )

    assert quote.symbol == "AAPL"
    assert quote.close == 104.0


def test_hindsight_move_model():
    move = HindsightMove(
        symbol="AAPL",
        entry_day=date(2026, 1, 2),
        exit_day=date(2026, 1, 3),
        entry_close=100.0,
        exit_close=110.0,
        return_pct=10.0,
        source="test",
    )

    assert move.return_pct == 10.0


def test_hindsight_optimizer_result_model():
    result = HindsightOptimizerResult(
        symbol="TEST",
        entry_day=date(2026, 1, 2),
        exit_day=date(2026, 1, 3),
        entry_price=100.0,
        exit_price=110.0,
        return_pct=10.0,
        return_multiple=1.1,
        starting_cash=100.0,
        ending_cash=110.0,
        target_cash=DEFAULT_TARGET_CASH,
        required_multiple=REQUIRED_MULTIPLE_TO_DEFAULT_TARGET,
        achieved_multiple=1.1,
        target_achieved=False,
        distance_from_target=DEFAULT_TARGET_CASH - 110.0,
        source="test",
        fetched_at=datetime(2026, 1, 10, 12, 0, 0),
        universe_limited_warning="small universe",
    )

    assert result.target_achieved is False
    assert result.distance_from_target == DEFAULT_TARGET_CASH - 110.0


def test_strategy_signal_model():
    signal = StrategySignal(
        signal_day=date(2026, 1, 2),
        symbol="AAPL",
        score=1.5,
        reason="test signal",
    )

    assert signal.symbol == "AAPL"


def test_paper_trade_model():
    trade = PaperTrade(
        signal_day=date(2026, 1, 1),
        entry_day=date(2026, 1, 2),
        exit_day=date(2026, 1, 3),
        symbol="AAPL",
        entry_price=100.0,
        exit_price=110.0,
        shares=1.0,
        starting_cash=100.0,
        ending_cash=110.0,
        return_pct=10.0,
    )

    assert trade.ending_cash == 110.0


def test_backtest_summary_model():
    summary = BacktestSummary(
        starting_cash=100.0,
        ending_cash=150.0,
        return_pct=50.0,
        trade_count=5,
        max_drawdown_pct=12.5,
        generated_at=datetime(2026, 1, 10, 12, 0, 0),
        mode="walk_forward",
    )

    assert summary.ending_cash == 150.0


def test_default_target_constants():
    assert DEFAULT_STARTING_CASH == 100.0
    assert DEFAULT_TARGET_CASH == 100_000_000.0
    assert REQUIRED_MULTIPLE_TO_DEFAULT_TARGET == 1_000_000.0
