"""Public input and output data-transfer objects.

All DTOs are zero-logic: no __post_init__ validation. Validation is server-side.
Round-trip serialization (asdict + reconstruct) is supported for all non-DataFrame fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# ExecutionMode
# ---------------------------------------------------------------------------

@dataclass
class ExecutionMode:
    """How a trade entry or exit price is determined.

    anchor: reference price point ('close-1', 'open', 'close').
    window: sub-bar periods from anchor (positive = after, negative = before).
    fill:   price resolution algorithm ('exact', 'tp', 'adverse', 'random').
    """

    anchor: str = "open"
    window: int = 0
    fill: str = "exact"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ExecutionMode":
        return cls(**d)


# ---------------------------------------------------------------------------
# ExecutionCosts
# ---------------------------------------------------------------------------

@dataclass
class ExecutionCosts:
    """Per-trade execution cost parameters.

    slippage_bps:          market-impact slippage in basis points.
    fee_pct:               round-trip commission as a fraction of notional (e.g. 0.001 = 0.1%).
    vol_scaled_slippage:   scale slippage by realised vol of the bar series.
    vol_slippage_lookback: rolling-window length for the vol estimate (bars).
    """

    slippage_bps: float = 0.0
    fee_pct: float = 0.0
    vol_scaled_slippage: bool = False
    vol_slippage_lookback: int = 20

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ExecutionCosts":
        return cls(**d)
