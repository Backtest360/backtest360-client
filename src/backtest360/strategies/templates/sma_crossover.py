"""SMA crossover starter template.

Enter long when fast SMA crosses above slow SMA; exit when it crosses back below.
Uses cross_above / cross_below transform indicators chained off two SMA technicals.
Long-only, daily bars.

Example::

    from backtest360.strategies import sma_crossover
    strategy = sma_crossover(fast=10, slow=50)
"""

from __future__ import annotations

from backtest360.dtos import Indicator, Strategy


def sma_crossover(fast: int = 10, slow: int = 50) -> Strategy:
    """Moving-average crossover long-only strategy.

    Args:
        fast: Fast SMA period (must be < slow).
        slow: Slow SMA period.
    """
    return Strategy(
        name="sma_crossover",
        description=(
            f"Buy when SMA({fast}) crosses above SMA({slow}); "
            f"sell when it crosses back below. Long-only."
        ),
        indicators=[
            Indicator(id="sma_fast", name="sma", params={"period": fast}, upstream=[]),
            Indicator(id="sma_slow", name="sma", params={"period": slow}, upstream=[]),
            Indicator(id="x_above", name="cross_above", params={}, upstream=["sma_fast", "sma_slow"]),
            Indicator(id="x_below", name="cross_below", params={}, upstream=["sma_fast", "sma_slow"]),
        ],
        condition_tree={
            "long_entry":  {"op": "leaf", "expr": "x_above > 0"},
            "long_exit":   {"op": "leaf", "expr": "x_below > 0"},
            "short_entry": None,
            "short_exit":  None,
        },
        defaults={"open_hour": 9.5, "close_hour": 16.0},
    )
