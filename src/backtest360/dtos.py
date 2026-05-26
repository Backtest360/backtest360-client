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


# ---------------------------------------------------------------------------
# BadDataReport
# ---------------------------------------------------------------------------

@dataclass
class BadDataReport:
    """Summary of bad-data bars encountered during run_backtest()."""

    count: int = 0
    entries: list = field(default_factory=list)    # list[BadDataEntry] (or raw dicts from server)
    policy: str = ""                               # 'raise' or 'zero'

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "entries": [
                e.to_dict() if isinstance(e, BadDataEntry) else e
                for e in self.entries
            ],
            "policy": self.policy,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BadDataReport":
        entries = [
            BadDataEntry.from_dict(e) if isinstance(e, dict) else e
            for e in d.get("entries", [])
        ]
        return cls(count=d.get("count", 0), entries=entries, policy=d.get("policy", ""))


# ---------------------------------------------------------------------------
# OffAnchorReport
# ---------------------------------------------------------------------------

@dataclass
class OffAnchorReport:
    """Summary of bars where the open/close anchor was missing and the lenient fallback fired."""

    open_count: int = 0
    close_count: int = 0
    events: list = field(default_factory=list)    # list[OffAnchorEvent] (or raw dicts from server)
    strict: bool = False

    def to_dict(self) -> dict:
        return {
            "open_count": self.open_count,
            "close_count": self.close_count,
            "events": [
                e.to_dict() if isinstance(e, OffAnchorEvent) else e
                for e in self.events
            ],
            "strict": self.strict,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OffAnchorReport":
        events = [
            OffAnchorEvent.from_dict(e) if isinstance(e, dict) else e
            for e in d.get("events", [])
        ]
        return cls(
            open_count=d.get("open_count", 0),
            close_count=d.get("close_count", 0),
            events=events,
            strict=d.get("strict", False),
        )


# ---------------------------------------------------------------------------
# SignalResult
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    """Diagnostic output of the signal generator.

    Populated when include_per_bar_df=True is set in BacktestConfig.
    Series fields are None by default (omitted from default responses).
    """

    long_entry_fired: Optional[pd.Series] = None
    long_exit_fired: Optional[pd.Series] = None
    short_entry_fired: Optional[pd.Series] = None
    short_exit_fired: Optional[pd.Series] = None

    @classmethod
    def from_dict(cls, d: dict) -> "SignalResult":
        """Reconstruct from the API signal_diagnostics sub-dict."""
        def _to_series(v: Optional[list]) -> Optional[pd.Series]:
            if v is None:
                return None
            return pd.Series(v, dtype=bool)
        return cls(
            long_entry_fired=_to_series(d.get("long_entry_fired")),
            long_exit_fired=_to_series(d.get("long_exit_fired")),
            short_entry_fired=_to_series(d.get("short_entry_fired")),
            short_exit_fired=_to_series(d.get("short_exit_fired")),
        )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@dataclass
class Statistics:
    """120+ performance metrics returned by the engine.

    All fields are Optional[float | int | str] so that benchmark-only metrics
    (alpha, beta, capture_ratio, ...) are simply None when no benchmark was supplied.
    Snake_case names map directly to the engine's FIELD_REGISTRY keys.
    """

    # Period
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_periods: Optional[int] = None

    # Returns & Performance
    total_return: Optional[float] = None
    cagr: Optional[float] = None
    mtd: Optional[float] = None
    ytd: Optional[float] = None
    ret_1m: Optional[float] = None
    ret_3m: Optional[float] = None
    ret_6m: Optional[float] = None
    ret_1y: Optional[float] = None
    ret_3y: Optional[float] = None
    ret_5y: Optional[float] = None
    ret_10y: Optional[float] = None
    exp_ret_avg: Optional[float] = None
    exp_ret_comp: Optional[float] = None
    gross_return: Optional[float] = None
    net_return: Optional[float] = None

    # Risk Metrics
    vol: Optional[float] = None
    vol_ann: Optional[float] = None
    parkinson_vol: Optional[float] = None
    parkinson_vol_ann: Optional[float] = None
    yang_zhang_vol: Optional[float] = None
    yang_zhang_vol_ann: Optional[float] = None
    max_drawdown: Optional[float] = None
    length_of_max_dd: Optional[int] = None
    recovery_of_max_dd: Optional[int] = None
    longest_dd: Optional[int] = None
    longest_recovery: Optional[int] = None
    avg_drawdown: Optional[float] = None
    avg_dd_length: Optional[int] = None
    avg_dd_recovery: Optional[int] = None
    avg_5_worst_dd: Optional[float] = None
    avg_5_worst_dd_length: Optional[int] = None
    avg_5_worst_dd_recovery: Optional[int] = None
    pct_dd_lt_5: Optional[float] = None
    pct_dd_lt_10: Optional[float] = None
    var_1pct: Optional[float] = None
    var_5pct: Optional[float] = None
    es_1pct: Optional[float] = None
    es_5pct: Optional[float] = None

    # Risk-Adjusted Returns
    sharpe_ratio: Optional[float] = None
    sharpe_se: Optional[float] = None
    sharpe_t_stat: Optional[float] = None
    sharpe_p_val: Optional[float] = None
    sharpe_lo: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None

    # Win/Loss Statistics
    win_rate: Optional[float] = None
    avg_up_day: Optional[float] = None
    avg_down_day: Optional[float] = None
    avg_daily_return: Optional[float] = None
    reward_to_risk: Optional[float] = None
    min_win_rate: Optional[float] = None
    expectancy: Optional[float] = None
    best_day: Optional[float] = None
    worst_day: Optional[float] = None
    best_month: Optional[float] = None
    worst_month: Optional[float] = None
    best_year: Optional[float] = None
    worst_year: Optional[float] = None
    avg_up_month: Optional[float] = None
    avg_down_month: Optional[float] = None
    avg_up_year: Optional[float] = None
    avg_down_year: Optional[float] = None
    win_pct_12m: Optional[float] = None
    win_pct_year: Optional[float] = None

    # Distribution
    skewness: Optional[float] = None
    skew_filtered: Optional[float] = None
    skew_no_outliers: Optional[float] = None
    skew_winsorized: Optional[float] = None
    skew_upper_tail: Optional[float] = None
    skew_lower_tail: Optional[float] = None
    kurtosis: Optional[float] = None
    mean: Optional[float] = None
    upper_tail_mean: Optional[float] = None
    lower_tail_mean: Optional[float] = None
    median: Optional[float] = None
    p10: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None

    # Market Exposure
    datapoints: Optional[int] = None
    trading_days: Optional[int] = None
    trade_pct: Optional[float] = None
    losing_streak_hist: Optional[int] = None
    losing_streak: Optional[int] = None
    kelly: Optional[float] = None
    half_kelly: Optional[float] = None
    quarter_kelly: Optional[float] = None
    days_in_position: Optional[int] = None
    days_out: Optional[int] = None
    days_long: Optional[int] = None
    days_short: Optional[int] = None
    time_in_market_pct: Optional[float] = None
    avg_position_size: Optional[float] = None
    avg_exposure: Optional[float] = None
    return_per_day_in_market: Optional[float] = None
    avg_return_in_market: Optional[float] = None
    avg_return_long_days: Optional[float] = None
    avg_return_short_days: Optional[float] = None
    position_source: Optional[str] = None

    # Trade Statistics
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    trade_win_rate: Optional[float] = None
    avg_trade_pnl: Optional[float] = None
    avg_win_pnl: Optional[float] = None
    avg_loss_pnl: Optional[float] = None
    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None
    profit_factor: Optional[float] = None
    avg_holding_days: Optional[float] = None
    pct_trades_1d: Optional[float] = None
    avg_ret_per_day_1d: Optional[float] = None
    total_ret_1d: Optional[float] = None
    pct_trades_le_2d: Optional[float] = None
    avg_ret_per_day_le_2d: Optional[float] = None
    total_ret_le_2d: Optional[float] = None
    pct_trades_le_3d: Optional[float] = None
    avg_ret_per_day_le_3d: Optional[float] = None
    total_ret_le_3d: Optional[float] = None
    max_consec_wins: Optional[int] = None
    max_consec_losses: Optional[int] = None

    # Signal Statistics
    total_signals: Optional[int] = None
    signal_win_rate: Optional[float] = None
    avg_signal_pnl: Optional[float] = None
    best_signal: Optional[float] = None
    worst_signal: Optional[float] = None
    signal_profit_factor: Optional[float] = None

    # Cost Summary
    total_trade_events: Optional[int] = None
    total_slippage: Optional[float] = None
    total_fees: Optional[float] = None
    total_costs: Optional[float] = None
    costs_as_pct_of_gross: Optional[float] = None
    avg_cost_per_event: Optional[float] = None

    # Benchmark Metrics (None when no benchmark supplied)
    beta: Optional[float] = None
    alpha: Optional[float] = None
    information_ratio: Optional[float] = None
    tracking_error: Optional[float] = None
    up_capture: Optional[float] = None
    down_capture: Optional[float] = None
    capture_ratio: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Statistics":
        known = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# RunResult
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    """Output of the bar-by-bar loop. Wraps per-bar series + trade log.

    signal_bars_per_year is inlined here (not on a separate MarketMeta object)
    so customers don't need to import internal engine types.

    Series fields (returns, signals, equity) are None by default and only
    populated when include_per_bar_df=True in BacktestConfig.
    """

    trades: list = field(default_factory=list)     # list[Trade]
    signal_bars_per_year: Optional[int] = None
    returns: Optional[pd.Series] = None            # net log returns per bar
    signals: Optional[pd.Series] = None            # {-1, 0, 1} per bar
    equity: Optional[pd.Series] = None             # cumulative equity curve
    bad_data: Optional[BadDataReport] = None
    off_anchors: Optional[OffAnchorReport] = None

    @classmethod
    def from_dict(cls, d: dict) -> "RunResult":
        trades = [
            Trade.from_dict(t) if isinstance(t, dict) else t
            for t in d.get("trades", [])
        ]

        def _series(key: str) -> Optional[pd.Series]:
            v = d.get(key)
            return pd.Series(v, dtype=float) if v is not None else None

        bad_data = (
            BadDataReport.from_dict(d["bad_data"])
            if d.get("bad_data") else None
        )
        off_anchors = (
            OffAnchorReport.from_dict(d["off_anchors"])
            if d.get("off_anchors") else None
        )
        return cls(
            trades=trades,
            signal_bars_per_year=d.get("signal_bars_per_year"),
            returns=_series("returns"),
            signals=_series("signals"),
            equity=_series("equity"),
            bad_data=bad_data,
            off_anchors=off_anchors,
        )


# ---------------------------------------------------------------------------
# BacktestResult
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    """Complete output of a backtest — top-level SDK response object."""

    run_result: Optional[RunResult] = None
    statistics: Optional[Statistics] = None
    signal_result: Optional[SignalResult] = None   # None for precomputed signals

    @classmethod
    def from_dict(cls, d: dict) -> "BacktestResult":
        run_result = (
            RunResult.from_dict(d["run_result"])
            if d.get("run_result") else None
        )
        statistics = (
            Statistics.from_dict(d["stats"])
            if d.get("stats") else None
        )
        signal_result = (
            SignalResult.from_dict(d["signal_diagnostics"])
            if d.get("signal_diagnostics") else None
        )
        return cls(run_result=run_result, statistics=statistics, signal_result=signal_result)
