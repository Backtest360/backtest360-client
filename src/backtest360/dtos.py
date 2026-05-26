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


# ---------------------------------------------------------------------------
# RiskControls
# ---------------------------------------------------------------------------

@dataclass
class RiskControls:
    """Per-strategy risk controls applied inside the backtest loop.

    stop_type:           stop-loss type: 'fixed', 'trailing', 'atr', 'trailing_atr', or None.
    stop_value:          for fixed/trailing, the percentage loss; for atr/trailing_atr, ATR multiplier.
    stop_atr_period:     ATR period (only when stop_type is 'atr' or 'trailing_atr').
    stop_reentry:        reentry rule after stop: 'immediate', 'next_signal', 'cooldown'.
    stop_cooldown_bars:  bars to wait when stop_reentry='cooldown'.
    max_drawdown_limit:  halt trading when cumulative drawdown exceeds this fraction.
    """

    stop_type: Optional[str] = None
    stop_value: Optional[float] = None
    stop_atr_period: int = 14
    stop_reentry: str = "immediate"
    stop_cooldown_bars: int = 0
    max_drawdown_limit: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RiskControls":
        return cls(**d)


# ---------------------------------------------------------------------------
# PositionSizing
# ---------------------------------------------------------------------------

@dataclass
class PositionSizing:
    """Position sizing parameters.

    position_weight:     fixed fraction of capital to allocate (1.0 = fully invested).
    vol_target:          annualised volatility target (e.g. 0.15 = 15%); None = disabled.
    vol_target_lookback: rolling-window length for the vol estimate (bars).
    leverage_limit:      maximum gross leverage multiple; None = uncapped.
    """

    position_weight: float = 1.0
    vol_target: Optional[float] = None
    vol_target_lookback: int = 20
    leverage_limit: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PositionSizing":
        return cls(**d)


# ---------------------------------------------------------------------------
# AssetInfo
# ---------------------------------------------------------------------------

@dataclass
class AssetInfo:
    """Optional metadata about the asset being backtested.

    All fields default to 'UNKNOWN' / True so that Tier-A customers
    (BYO DataFrame) never need to construct one explicitly.
    """

    ticker: str = "UNKNOWN"
    name: str = "UNKNOWN"
    asset_class: str = "UNKNOWN"   # 'stocks', 'crypto', 'forex', 'indices'
    exchange: str = "UNKNOWN"
    currency: str = "UNKNOWN"
    active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AssetInfo":
        return cls(**d)
