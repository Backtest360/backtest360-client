"""Public input and output data-transfer objects.

All DTOs are zero-logic: no __post_init__ validation. Validation is server-side.
Round-trip serialization (asdict + reconstruct) is supported for all non-DataFrame fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import cast

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
    def from_dict(cls, d: dict) -> ExecutionMode:
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
    def from_dict(cls, d: dict) -> ExecutionCosts:
        return cls(**d)


# ---------------------------------------------------------------------------
# RiskControls
# ---------------------------------------------------------------------------


@dataclass
class RiskControls:
    """Per-strategy risk controls applied inside the backtest loop.

    stop_type:           stop-loss type: 'fixed', 'trailing', 'atr', 'trailing_atr', or None.
    stop_value:          percentage loss (fixed/trailing) or ATR multiplier (atr/trailing_atr).
    stop_atr_period:     ATR period (only when stop_type is 'atr' or 'trailing_atr').
    stop_reentry:        reentry rule after stop: 'immediate', 'next_signal', 'cooldown'.
    stop_cooldown_bars:  bars to wait when stop_reentry='cooldown'.
    max_drawdown_limit:  halt trading when cumulative drawdown exceeds this fraction.
    """

    stop_type: str | None = None
    stop_value: float | None = None
    stop_atr_period: int = 14
    stop_reentry: str = "immediate"
    stop_cooldown_bars: int = 0
    max_drawdown_limit: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> RiskControls:
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
    vol_target: float | None = None
    vol_target_lookback: int = 20
    leverage_limit: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> PositionSizing:
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
    asset_class: str = "UNKNOWN"  # 'stocks', 'crypto', 'forex', 'indices'
    exchange: str = "UNKNOWN"
    currency: str = "UNKNOWN"
    active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> AssetInfo:
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

    ohlcv: pd.DataFrame | None = None
    asset_info: AssetInfo = field(default_factory=AssetInfo)
    is_24h: bool | None = None
    session_open: float | None = None
    session_close: float | None = None
    trading_days_per_year: int | None = None
    bar_frequency: str | None = None
    source_bars_per_year: int | None = None
    missing_bars: int = 0
    bad_prices: int = 0
    quality_warnings: list = field(default_factory=list)

    # .ts is a thin alias over .ohlcv (preserves dataclasses.replace() compat)
    @property
    def ts(self) -> pd.DataFrame | None:
        return self.ohlcv

    @ts.setter
    def ts(self, df: pd.DataFrame | None) -> None:
        self.ohlcv = df

    def load(self, df: pd.DataFrame) -> MarketData:
        """Populate fields from a raw OHLCV DataFrame via auto-detection.

        Runs: bar-frequency detection, market-hours detection,
        trading-days-per-year detection, and data-quality assessment.
        Returns self to allow chaining.
        """
        import pandas as pd

        from backtest360._detection import (
            assess_data_quality,
            detect_bar_frequency,
            detect_market_hours,
            detect_trading_days_per_year,
        )

        self.ohlcv = df

        bar_freq_info = detect_bar_frequency(cast(pd.DatetimeIndex, df.index))
        bar_frequency = bar_freq_info["label"]
        self.bar_frequency = bar_frequency

        market_hours = detect_market_hours(df)
        self.is_24h = market_hours["is_24h"]
        self.session_open = market_hours["detected_open_hour"]
        self.session_close = market_hours["detected_close_hour"]

        tdpy = detect_trading_days_per_year(df, self.is_24h)
        self.trading_days_per_year = tdpy

        bars_per_day = bar_freq_info["bars_per_day"]
        if "bars_per_year" in bar_freq_info:
            self.source_bars_per_year = bar_freq_info["bars_per_year"]
        elif tdpy is None:
            self.source_bars_per_year = None
        elif self.is_24h:
            self.source_bars_per_year = int(tdpy * bars_per_day)
        else:
            session_hours = self.session_close - self.session_open
            if session_hours > 0:
                session_bars_per_day = max(1, int(session_hours * bars_per_day / 24))
            else:
                session_bars_per_day = int(bars_per_day)
            self.source_bars_per_year = tdpy * session_bars_per_day

        missing_bars, bad_prices, warnings = assess_data_quality(
            df,
            bar_frequency,
            self.is_24h,
            self.session_open or 0.0,
            self.session_close or 0.0,
        )
        self.missing_bars = missing_bars
        self.bad_prices = bad_prices
        self.quality_warnings = warnings

        return self


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
    def from_dict(cls, d: dict) -> Indicator:
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
    condition_tree: dict | None = None
    indicators: list = field(default_factory=list)  # list[Indicator]
    precomputed_signals: object | None = None  # pd.Series — not serialized via asdict
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
                ind.to_dict() if isinstance(ind, Indicator) else ind for ind in self.indicators
            ],
            "requires": self.requires,
            "defaults": self.defaults,
            "locked_params": list(self.locked_params),
            "tier": self.tier,
            # precomputed_signals excluded — wire format handled by BacktestClient
        }

    @classmethod
    def from_dict(cls, d: dict) -> Strategy:
        indicators = [
            Indicator.from_dict(i) if isinstance(i, dict) else i for i in d.get("indicators", [])
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
    entry_mode: ExecutionMode | None = None  # None → open/exact
    exit_mode: ExecutionMode | None = None  # None → close/exact
    costs: ExecutionCosts | None = None  # None → zero costs
    risk: RiskControls | None = None  # None → no risk controls
    sizing: PositionSizing | None = None  # None → full weight
    open_hour: float | None = None  # None → auto-detected
    close_hour: float | None = None  # None → auto-detected
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
    def from_dict(cls, d: dict) -> BacktestConfig:
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
    entry_date: str | None = None  # ISO timestamp
    direction: int = 0  # +1 long, -1 short
    entry_price: float = 0.0
    exit_bar: int = 0
    exit_date: str | None = None  # ISO timestamp
    exit_price: float = 0.0
    exit_reason: str = ""  # 'exit_signal', 'stop', 'flip', 'end_of_data'
    holding_bars: int = 0
    return_gross: float = 0.0  # log return before costs
    return_net: float = 0.0  # log return after costs
    cumulative_pnl: float = 0.0  # running sum of return_net to this trade

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Trade:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# BadDataEntry
# ---------------------------------------------------------------------------


@dataclass
class BadDataEntry:
    """A single bad-data bar from the backtest loop."""

    bar_index: int = 0
    bar_state: str = ""  # 'FLAT', 'ENTRY', 'HOLD', 'EXIT', 'FLIP'
    reason: str = ""  # human-readable, e.g. "start=nan" or "end=-5.0"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> BadDataEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# OffAnchorEvent
# ---------------------------------------------------------------------------


@dataclass
class OffAnchorEvent:
    """A single bar where the configured open/close anchor was missing
    and the lenient fallback (first/last sub-bar) fired."""

    bar_idx: int = 0
    anchor: str = ""  # 'open' or 'close'
    target_hour: float = 0.0
    timestamp: str | None = None  # ISO timestamp of the sub-bar group
    chosen_idx: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> OffAnchorEvent:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# BadDataReport
# ---------------------------------------------------------------------------


@dataclass
class BadDataReport:
    """Summary of bad-data bars encountered during run_backtest()."""

    count: int = 0
    entries: list = field(default_factory=list)  # list[BadDataEntry] (or raw dicts from server)
    policy: str = ""  # 'raise' or 'zero'

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "entries": [e.to_dict() if isinstance(e, BadDataEntry) else e for e in self.entries],
            "policy": self.policy,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BadDataReport:
        entries = [
            BadDataEntry.from_dict(e) if isinstance(e, dict) else e for e in d.get("entries", [])
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
    events: list = field(default_factory=list)  # list[OffAnchorEvent] (or raw dicts from server)
    strict: bool = False

    def to_dict(self) -> dict:
        return {
            "open_count": self.open_count,
            "close_count": self.close_count,
            "events": [e.to_dict() if isinstance(e, OffAnchorEvent) else e for e in self.events],
            "strict": self.strict,
        }

    @classmethod
    def from_dict(cls, d: dict) -> OffAnchorReport:
        events = [
            OffAnchorEvent.from_dict(e) if isinstance(e, dict) else e for e in d.get("events", [])
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

    long_entry_fired: pd.Series | None = None
    long_exit_fired: pd.Series | None = None
    short_entry_fired: pd.Series | None = None
    short_exit_fired: pd.Series | None = None

    @classmethod
    def from_dict(cls, d: dict) -> SignalResult:
        """Reconstruct from the API signal_diagnostics sub-dict."""

        def _to_series(v: list | None) -> pd.Series | None:
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
    start_date: str | None = None
    end_date: str | None = None
    total_periods: int | None = None

    # Returns & Performance
    total_return: float | None = None
    cagr: float | None = None
    mtd: float | None = None
    ytd: float | None = None
    ret_1m: float | None = None
    ret_3m: float | None = None
    ret_6m: float | None = None
    ret_1y: float | None = None
    ret_3y: float | None = None
    ret_5y: float | None = None
    ret_10y: float | None = None
    exp_ret_avg: float | None = None
    exp_ret_comp: float | None = None
    gross_return: float | None = None
    net_return: float | None = None

    # Risk Metrics
    vol: float | None = None
    vol_ann: float | None = None
    parkinson_vol: float | None = None
    parkinson_vol_ann: float | None = None
    yang_zhang_vol: float | None = None
    yang_zhang_vol_ann: float | None = None
    max_drawdown: float | None = None
    length_of_max_dd: int | None = None
    recovery_of_max_dd: int | None = None
    longest_dd: int | None = None
    longest_recovery: int | None = None
    avg_drawdown: float | None = None
    avg_dd_length: int | None = None
    avg_dd_recovery: int | None = None
    avg_5_worst_dd: float | None = None
    avg_5_worst_dd_length: int | None = None
    avg_5_worst_dd_recovery: int | None = None
    pct_dd_lt_5: float | None = None
    pct_dd_lt_10: float | None = None
    var_1pct: float | None = None
    var_5pct: float | None = None
    es_1pct: float | None = None
    es_5pct: float | None = None

    # Risk-Adjusted Returns
    sharpe_ratio: float | None = None
    sharpe_se: float | None = None
    sharpe_t_stat: float | None = None
    sharpe_p_val: float | None = None
    sharpe_lo: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None

    # Win/Loss Statistics
    win_rate: float | None = None
    avg_up_day: float | None = None
    avg_down_day: float | None = None
    avg_daily_return: float | None = None
    reward_to_risk: float | None = None
    min_win_rate: float | None = None
    expectancy: float | None = None
    best_day: float | None = None
    worst_day: float | None = None
    best_month: float | None = None
    worst_month: float | None = None
    best_year: float | None = None
    worst_year: float | None = None
    avg_up_month: float | None = None
    avg_down_month: float | None = None
    avg_up_year: float | None = None
    avg_down_year: float | None = None
    win_pct_12m: float | None = None
    win_pct_year: float | None = None

    # Distribution
    skewness: float | None = None
    skew_filtered: float | None = None
    skew_no_outliers: float | None = None
    skew_winsorized: float | None = None
    skew_upper_tail: float | None = None
    skew_lower_tail: float | None = None
    kurtosis: float | None = None
    mean: float | None = None
    upper_tail_mean: float | None = None
    lower_tail_mean: float | None = None
    median: float | None = None
    p10: float | None = None
    p25: float | None = None
    p75: float | None = None
    p90: float | None = None

    # Market Exposure
    datapoints: int | None = None
    trading_days: int | None = None
    trade_pct: float | None = None
    losing_streak_hist: int | None = None
    losing_streak: int | None = None
    kelly: float | None = None
    half_kelly: float | None = None
    quarter_kelly: float | None = None
    days_in_position: int | None = None
    days_out: int | None = None
    days_long: int | None = None
    days_short: int | None = None
    time_in_market_pct: float | None = None
    avg_position_size: float | None = None
    avg_exposure: float | None = None
    return_per_day_in_market: float | None = None
    avg_return_in_market: float | None = None
    avg_return_long_days: float | None = None
    avg_return_short_days: float | None = None
    position_source: str | None = None

    # Trade Statistics
    total_trades: int | None = None
    winning_trades: int | None = None
    losing_trades: int | None = None
    trade_win_rate: float | None = None
    avg_trade_pnl: float | None = None
    avg_win_pnl: float | None = None
    avg_loss_pnl: float | None = None
    best_trade: float | None = None
    worst_trade: float | None = None
    profit_factor: float | None = None
    avg_holding_days: float | None = None
    pct_trades_1d: float | None = None
    avg_ret_per_day_1d: float | None = None
    total_ret_1d: float | None = None
    pct_trades_le_2d: float | None = None
    avg_ret_per_day_le_2d: float | None = None
    total_ret_le_2d: float | None = None
    pct_trades_le_3d: float | None = None
    avg_ret_per_day_le_3d: float | None = None
    total_ret_le_3d: float | None = None
    max_consec_wins: int | None = None
    max_consec_losses: int | None = None

    # Signal Statistics
    total_signals: int | None = None
    signal_win_rate: float | None = None
    avg_signal_pnl: float | None = None
    best_signal: float | None = None
    worst_signal: float | None = None
    signal_profit_factor: float | None = None

    # Cost Summary
    total_trade_events: int | None = None
    total_slippage: float | None = None
    total_fees: float | None = None
    total_costs: float | None = None
    costs_as_pct_of_gross: float | None = None
    avg_cost_per_event: float | None = None

    # Benchmark Metrics (None when no benchmark supplied)
    beta: float | None = None
    alpha: float | None = None
    information_ratio: float | None = None
    tracking_error: float | None = None
    up_capture: float | None = None
    down_capture: float | None = None
    capture_ratio: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Statistics:
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

    trades: list = field(default_factory=list)  # list[Trade]
    signal_bars_per_year: int | None = None
    returns: pd.Series | None = None  # net log returns per bar
    signals: pd.Series | None = None  # {-1, 0, 1} per bar
    equity: pd.Series | None = None  # cumulative equity curve
    bad_data: BadDataReport | None = None
    off_anchors: OffAnchorReport | None = None

    @classmethod
    def from_dict(cls, d: dict) -> RunResult:
        trades = [Trade.from_dict(t) if isinstance(t, dict) else t for t in d.get("trades", [])]

        def _series(key: str) -> pd.Series | None:
            v = d.get(key)
            return pd.Series(v, dtype=float) if v is not None else None

        bad_data = BadDataReport.from_dict(d["bad_data"]) if d.get("bad_data") else None
        off_anchors = OffAnchorReport.from_dict(d["off_anchors"]) if d.get("off_anchors") else None
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

    run_result: RunResult | None = None
    statistics: Statistics | None = None
    signal_result: SignalResult | None = None  # None for precomputed signals

    @classmethod
    def from_dict(cls, d: dict) -> BacktestResult:
        # Engine returns flat shape: trades/series/stats at top level (no run_result wrapper).
        series = d.get("series", {})
        run_dict: dict = {
            "trades": d.get("trades", []),
            "signal_bars_per_year": d.get("signal_bars_per_year"),
            "returns": series.get("returns"),
            "signals": series.get("signals"),
            "equity": series.get("equity"),
        }
        if d.get("off_anchors"):
            run_dict["off_anchors"] = d["off_anchors"]
        run_result = RunResult.from_dict(run_dict)
        statistics = Statistics.from_dict(d["stats"]) if d.get("stats") else None
        signal_result = (
            SignalResult.from_dict(d["signal_diagnostics"]) if d.get("signal_diagnostics") else None
        )
        return cls(run_result=run_result, statistics=statistics, signal_result=signal_result)


# ---------------------------------------------------------------------------
# ValidationIssue
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """A single validation finding on a strategy or config.

    Distinct from the SDK ``ValidationError`` exception class — this is a
    data object returned inside ``ValidationResult``, not an exception.
    """

    code: str = ""
    message: str = ""
    field: str | None = None  # which field triggered the issue, if known

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ValidationIssue:
        return cls(
            code=d.get("code", ""),
            message=d.get("message", ""),
            field=d.get("field"),
        )


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Output of BacktestClient.validate_strategy()."""

    valid: bool = True
    issues: list = field(default_factory=list)  # list[ValidationIssue]

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "issues": [i.to_dict() if isinstance(i, ValidationIssue) else i for i in self.issues],
        }

    @classmethod
    def from_dict(cls, d: dict) -> ValidationResult:
        issues = [
            ValidationIssue.from_dict(i) if isinstance(i, dict) else i for i in d.get("issues", [])
        ]
        return cls(valid=d.get("valid", True), issues=issues)


# ---------------------------------------------------------------------------
# LatestSignalResult
# ---------------------------------------------------------------------------


@dataclass
class LatestSignalResult:
    """Output of BacktestClient.latest_signal()."""

    signal: int = 0  # {-1, 0, 1}
    bar_timestamp: str | None = None  # ISO timestamp of the last signal bar
    long_entry_fired: bool | None = None
    long_exit_fired: bool | None = None
    short_entry_fired: bool | None = None
    short_exit_fired: bool | None = None
    warmup_bars_used: int | None = None
    created_at: str | None = None  # ISO timestamp — when the signal was computed

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> LatestSignalResult:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
