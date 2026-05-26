"""Buy-and-hold starter template.

Always long — enters on bar 1, never exits. Useful as a benchmark baseline
to compare against active strategies.

Example::

    from backtest360.strategies import buy_and_hold
    result = client.backtest(buy_and_hold(), config, market_data)
"""

from __future__ import annotations

from backtest360.dtos import Indicator, Strategy


def buy_and_hold() -> Strategy:
    """Buy-and-hold baseline strategy (always long, no exits).

    The long_entry condition (close > 0) is trivially true for any real asset.
    long_exit is None — the position is held through the entire backtest.
    """
    return Strategy(
        name="buy_and_hold",
        description="Always long — enters bar 1 and holds. Use as a buy-and-hold benchmark.",
        indicators=[
            Indicator(id="close_prim", name="close", params={}, upstream=[]),
        ],
        condition_tree={
            "long_entry":  {"op": "leaf", "expr": "close_prim > 0"},
            "long_exit":   None,
            "short_entry": None,
            "short_exit":  None,
        },
    )
