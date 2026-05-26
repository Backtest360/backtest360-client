"""Donchian channel breakout starter template.

Enter long when close exceeds the N-period rolling high; exit when close
falls below the N-period rolling low. Uses rolling_max / rolling_min
transform indicators chained off the high / low primitives.
Long-only, daily bars.

Example::

    from backtest360.strategies import donchian_breakout
    strategy = donchian_breakout(period=20)
"""

from __future__ import annotations

from backtest360.dtos import Indicator, Strategy


def donchian_breakout(period: int = 20) -> Strategy:
    """Donchian channel breakout long-only strategy.

    Args:
        period: Rolling window for channel high and low.
    """
    return Strategy(
        name="donchian_breakout",
        description=(
            f"Enter long when close exceeds the {period}-bar rolling high; "
            f"exit when close falls below the {period}-bar rolling low."
        ),
        indicators=[
            Indicator(id="high_prim", name="high", params={}, upstream=[]),
            Indicator(id="low_prim",  name="low",  params={}, upstream=[]),
            Indicator(id="close_prim", name="close", params={}, upstream=[]),
            Indicator(id="dc_upper", name="rolling_max", params={"period": period}, upstream=["high_prim"]),
            Indicator(id="dc_lower", name="rolling_min", params={"period": period}, upstream=["low_prim"]),
        ],
        condition_tree={
            "long_entry":  {"op": "leaf", "expr": "close_prim > dc_upper"},
            "long_exit":   {"op": "leaf", "expr": "close_prim < dc_lower"},
            "short_entry": None,
            "short_exit":  None,
        },
        defaults={"open_hour": 9.5, "close_hour": 16.0},
    )
