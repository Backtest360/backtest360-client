"""RSI threshold long-only starter template.

Enter long when RSI(14) crosses below 30; exit when it crosses above 70.
Long-only, daily bars.

Example::

    from backtest360 import BacktestClient, BacktestConfig, MarketData
    from backtest360.strategies import rsi_threshold_long

    md = MarketData()
    md.load(df)
    result = BacktestClient(api_key="...").backtest(rsi_threshold_long(), BacktestConfig(), md)
"""

from __future__ import annotations

from backtest360.dtos import Indicator, Strategy


def rsi_threshold_long(
    period: int = 14,
    entry_threshold: float = 30.0,
    exit_threshold: float = 70.0,
) -> Strategy:
    """RSI mean-reversion long-only strategy.

    Args:
        period: RSI lookback period.
        entry_threshold: Enter long when RSI drops below this level.
        exit_threshold: Exit long when RSI rises above this level.
    """
    return Strategy(
        name="rsi_threshold_long",
        description=(
            f"Enter long when RSI({period}) < {entry_threshold}; "
            f"exit when RSI({period}) > {exit_threshold}. Long-only."
        ),
        indicators=[
            Indicator(id="rsi", name="rsi", params={"period": period}, upstream=[]),
        ],
        condition_tree={
            "long_entry": {"op": "leaf", "expr": f"rsi < {entry_threshold}"},
            "long_exit": {"op": "leaf", "expr": f"rsi > {exit_threshold}"},
            "short_entry": None,
            "short_exit": None,
        },
        defaults={"open_hour": 9.5, "close_hour": 16.0},
    )
