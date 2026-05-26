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


# ---------------------------------------------------------------------------
# MarketData
# ---------------------------------------------------------------------------

@dataclass
class MarketData:
    """OHLCV market data plus auto-detected market properties.

    All 11 fields default so ``MarketData()`` is a legal bare constructor.
    Call ``md.load(df)`` to populate fields from a raw OHLCV DataFrame.

    The ``.ts`` property is a thin alias for ``.ohlcv`` — use either name.
    """

    ohlcv: Optional[pd.DataFrame] = None
    asset_info: AssetInfo = field(default_factory=AssetInfo)
    is_24h: Optional[bool] = None
    session_open: Optional[float] = None
    session_close: Optional[float] = None
    trading_days_per_year: Optional[int] = None
    bar_frequency: Optional[str] = None
    source_bars_per_year: Optional[int] = None
    missing_bars: int = 0
    bad_prices: int = 0
    quality_warnings: list = field(default_factory=list)

    # .ts is a thin alias over .ohlcv (preserves dataclasses.replace() compat)
    @property
    def ts(self) -> Optional[pd.DataFrame]:
        return self.ohlcv

    @ts.setter
    def ts(self, df: Optional[pd.DataFrame]) -> None:
        self.ohlcv = df

    def load(self, df: pd.DataFrame) -> "MarketData":
        """Populate fields from a raw OHLCV DataFrame via auto-detection.

        Detection helpers are implemented in step 3.7.
        Returns self to allow chaining.
        """
        raise NotImplementedError("load() is implemented in step 3.7")


# ---------------------------------------------------------------------------
# Indicator
# ---------------------------------------------------------------------------

@dataclass
class Indicator:
    """A reference to a registered indicator, parameterized for a strategy.

    id:       unique identifier within the Strategy.indicators list; referenced
              by condition leaves in the condition_tree.
    name:     the registered indicator kind (e.g. 'RSI', 'SMA', 'ATR').
    params:   parameter overrides (e.g. {'lookback': 14}).
    upstream: list of Indicator ids this indicator depends on (for transforms).
    """

    id: str = ""
    name: str = ""
    params: dict = field(default_factory=dict)
    upstream: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Indicator":
        return cls(**d)


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

@dataclass
class Strategy:
    """Strategy signal logic — what to trade, not how.

    Two mutually exclusive signal forms (validation is server-side):
    - condition_tree + indicators: GUI-composable json-logic tree with 4 slots
      (long_entry, long_exit, short_entry, short_exit) referencing Indicator ids.
    - precomputed_signals: a pd.Series of {-1, 0, 1} indexed by signal bar.

    requires / defaults / locked_params: two-tier parameter resolution — the
    server applies these when resolving indicator params at backtest time.
    """

    name: str = ""
    description: str = ""
    condition_tree: Optional[dict] = None
    indicators: list = field(default_factory=list)     # list[Indicator]
    precomputed_signals: Optional[object] = None       # pd.Series — not serialized via asdict
    requires: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)
    locked_params: list = field(default_factory=list)  # list[str] — list for JSON compat
    tier: str = "customer"

    def to_dict(self) -> dict:
        """Serialize all non-DataFrame/Series fields."""
        return {
            "name": self.name,
            "description": self.description,
            "condition_tree": self.condition_tree,
            "indicators": [
                ind.to_dict() if isinstance(ind, Indicator) else ind
                for ind in self.indicators
            ],
            "requires": self.requires,
            "defaults": self.defaults,
            "locked_params": list(self.locked_params),
            "tier": self.tier,
            # precomputed_signals excluded — wire format handled by BacktestClient
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Strategy":
        indicators = [
            Indicator.from_dict(i) if isinstance(i, dict) else i
            for i in d.get("indicators", [])
        ]
        return cls(
            name=d.get("name", ""),
            description=d.get("description", ""),
            condition_tree=d.get("condition_tree"),
            indicators=indicators,
            requires=d.get("requires", {}),
            defaults=d.get("defaults", {}),
            locked_params=d.get("locked_params", []),
            tier=d.get("tier", "customer"),
        )


# ---------------------------------------------------------------------------
# BacktestConfig
# ---------------------------------------------------------------------------

@dataclass
class BacktestConfig:
    """Execution and risk configuration for a backtest — the HOW, not the WHAT.

    Strategy is passed separately to BacktestClient.backtest(); it is NOT a field
    here. The engine builds a full BacktestConfig internally when it combines these
    parameters with the strategy.

    Defaults produce a daily-signal, open-exact entry, close-exact exit backtest
    with no costs, no risk controls, and full position weighting.
    """

    signal_frequency: str = "daily"
    entry_mode: Optional[ExecutionMode] = None    # None → open/exact
    exit_mode: Optional[ExecutionMode] = None     # None → close/exact
    costs: Optional[ExecutionCosts] = None        # None → zero costs
    risk: Optional[RiskControls] = None           # None → no risk controls
    sizing: Optional[PositionSizing] = None       # None → full weight
    open_hour: Optional[float] = None             # None → auto-detected
    close_hour: Optional[float] = None            # None → auto-detected
    strict_anchors: bool = False
    risk_free_rate: float = 0.0
    on_bad_data: str = "raise"
    random_seed: int = 42
    include_per_bar_df: bool = False
    include_indicator_values: bool = False

    def to_dict(self) -> dict:
        return {
            "signal_frequency": self.signal_frequency,
            "entry_mode": self.entry_mode.to_dict() if self.entry_mode else None,
            "exit_mode": self.exit_mode.to_dict() if self.exit_mode else None,
            "costs": self.costs.to_dict() if self.costs else None,
            "risk": self.risk.to_dict() if self.risk else None,
            "sizing": self.sizing.to_dict() if self.sizing else None,
            "open_hour": self.open_hour,
            "close_hour": self.close_hour,
            "strict_anchors": self.strict_anchors,
            "risk_free_rate": self.risk_free_rate,
            "on_bad_data": self.on_bad_data,
            "random_seed": self.random_seed,
            "include_per_bar_df": self.include_per_bar_df,
            "include_indicator_values": self.include_indicator_values,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BacktestConfig":
        return cls(
            signal_frequency=d.get("signal_frequency", "daily"),
            entry_mode=ExecutionMode.from_dict(d["entry_mode"]) if d.get("entry_mode") else None,
            exit_mode=ExecutionMode.from_dict(d["exit_mode"]) if d.get("exit_mode") else None,
            costs=ExecutionCosts.from_dict(d["costs"]) if d.get("costs") else None,
            risk=RiskControls.from_dict(d["risk"]) if d.get("risk") else None,
            sizing=PositionSizing.from_dict(d["sizing"]) if d.get("sizing") else None,
            open_hour=d.get("open_hour"),
            close_hour=d.get("close_hour"),
            strict_anchors=d.get("strict_anchors", False),
            risk_free_rate=d.get("risk_free_rate", 0.0),
            on_bad_data=d.get("on_bad_data", "raise"),
            random_seed=d.get("random_seed", 42),
            include_per_bar_df=d.get("include_per_bar_df", False),
            include_indicator_values=d.get("include_indicator_values", False),
        )


# ===========================================================================
# OUTPUT DTOs
# ===========================================================================

# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    """A single completed trade from the backtest loop."""

    entry_bar: int = 0
    entry_date: Optional[str] = None       # ISO timestamp
    direction: int = 0                      # +1 long, -1 short
    entry_price: float = 0.0
    exit_bar: int = 0
    exit_date: Optional[str] = None        # ISO timestamp
    exit_price: float = 0.0
    exit_reason: str = ""                   # 'exit_signal', 'stop', 'flip', 'end_of_data'
    holding_bars: int = 0
    return_gross: float = 0.0              # log return before costs
    return_net: float = 0.0               # log return after costs
    cumulative_pnl: float = 0.0           # running sum of return_net to this trade

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Trade":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# BadDataEntry
# ---------------------------------------------------------------------------

@dataclass
class BadDataEntry:
    """A single bad-data bar from the backtest loop."""

    bar_index: int = 0
    bar_state: str = ""    # 'FLAT', 'ENTRY', 'HOLD', 'EXIT', 'FLIP'
    reason: str = ""       # human-readable, e.g. "start=nan" or "end=-5.0"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BadDataEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# OffAnchorEvent
# ---------------------------------------------------------------------------

@dataclass
class OffAnchorEvent:
    """A single bar where the configured open/close anchor was missing
    and the lenient fallback (first/last sub-bar) fired."""

    bar_idx: int = 0
    anchor: str = ""        # 'open' or 'close'
    target_hour: float = 0.0
    timestamp: Optional[str] = None    # ISO timestamp of the sub-bar group
    chosen_idx: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "OffAnchorEvent":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
