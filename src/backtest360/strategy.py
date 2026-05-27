"""Strategy builder and execution configuration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Execution configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Execution:
    """Execution timing — when signals are entered and exited.

    Args:
        entry: Bar anchor for entry fills. One of ``"open"``, ``"close"``,
            ``"vwap"``. Default ``"open"``.
        exit: Bar anchor for exit fills. Default ``"close"``.
        signal_frequency: Frequency at which the strategy generates signals.
            Common values: ``"daily"``, ``"hourly"``, ``"4h"``, ``"weekly"``.
            See ``GET /api/bar-frequencies`` for the full list.
        entry_window: Number of bars the engine attempts to fill after the
            entry anchor. Default ``0`` (fill on the anchor bar only).
        exit_window: Same for exits.
        fill: Fill price model. One of ``"exact"``, ``"worst"``, ``"best"``.
            Default ``"exact"``.

    See also:
        https://api.backtest360.com/docs for the full execution reference.

    Example:
        >>> Execution(entry="open", exit="close", signal_frequency="daily")
    """

    entry: str = "open"
    exit: str = "close"
    signal_frequency: str = "daily"
    entry_window: int = 0
    exit_window: int = 0
    fill: str = "exact"

    def to_wire(self) -> dict:
        return {
            "signal_frequency": self.signal_frequency,
            "entry_anchor":     self.entry,
            "entry_window":     self.entry_window,
            "entry_fill":       self.fill,
            "exit_anchor":      self.exit,
            "exit_window":      self.exit_window,
            "exit_fill":        self.fill,
        }


@dataclass
class Costs:
    """Transaction costs — slippage and fees.

    Args:
        slippage_bps: Slippage in basis points (10 = 0.1%). Applied adversely
            on every fill. Default ``0.0``.
        fee_pct: Round-trip fee as a fraction (0.001 = 0.1%). Deducted on
            entry and exit events. Default ``0.0``.
        vol_scaled_slippage: Scale slippage by rolling realised volatility.
            Default ``False``.
        vol_slippage_lookback: Lookback bars for vol-scaled slippage.
            Default ``20``.

    Example:
        >>> Costs(slippage_bps=2.5, fee_pct=0.001)
    """

    slippage_bps: float = 0.0
    fee_pct: float = 0.0
    vol_scaled_slippage: bool = False
    vol_slippage_lookback: int = 20

    def to_wire(self) -> dict:
        return {
            "slippage_bps":          self.slippage_bps,
            "fee_pct":               self.fee_pct,
            "vol_scaled_slippage":   self.vol_scaled_slippage,
            "vol_slippage_lookback": self.vol_slippage_lookback,
        }


@dataclass
class Risk:
    """Risk management — stops and drawdown protection.

    Args:
        stop: Stop type. One of ``"fixed_pct"``, ``"trailing_pct"``,
            ``"fixed_atr"``, ``"trailing_atr"``. ``None`` disables stops.
            See ``GET /api/stop-types`` for the full list.
        value: Stop distance — percent (e.g. ``0.05`` for 5%) or ATR multiple
            (e.g. ``2.5`` for 2.5× ATR), depending on ``stop``.
        atr_period: Lookback bars for ATR-based stops. Default ``None``.
        reentry: Re-enter after a stop-out. Default ``True``.
        cooldown_bars: Bars to wait before re-entering after a stop.
            Default ``0``.
        max_drawdown: Circuit-breaker drawdown limit (e.g. ``0.25`` = 25%).
            Flattens the position when the running drawdown exceeds this value.
            ``None`` disables it.

    Example:
        >>> Risk(stop="trailing_atr", value=2.5, atr_period=14)
        >>> Risk(stop="fixed_pct", value=0.05, max_drawdown=0.20)
    """

    stop: str | None = None
    value: float | None = None
    atr_period: int | None = None
    reentry: bool = True
    cooldown_bars: int = 0
    max_drawdown: float | None = None

    def to_wire(self) -> dict:
        d: dict = {
            "stop_reentry":      self.reentry,
            "stop_cooldown_bars": self.cooldown_bars,
        }
        if self.stop is not None:
            d["stop_type"] = self.stop
        if self.value is not None:
            d["stop_value"] = self.value
        if self.atr_period is not None:
            d["stop_atr_period"] = self.atr_period
        if self.max_drawdown is not None:
            d["max_drawdown_limit"] = self.max_drawdown
        return d


@dataclass
class Sizing:
    """Position sizing configuration.

    Args:
        weight: Fraction of capital deployed per position (1.0 = fully
            invested). Default ``1.0``.
        vol_target: Annualised volatility target for vol-targeting sizing.
            ``None`` disables vol targeting. Example: ``0.15`` for 15%.
        vol_target_lookback: Lookback bars for realised vol estimate.
            Default ``20``.
        leverage_limit: Maximum leverage cap. Default ``1.0``.

    Example:
        >>> Sizing(weight=0.5)
        >>> Sizing(vol_target=0.15, leverage_limit=2.0)
    """

    weight: float = 1.0
    vol_target: float | None = None
    vol_target_lookback: int = 20
    leverage_limit: float = 1.0

    def to_wire(self) -> dict:
        d: dict = {
            "position_weight":     self.weight,
            "leverage_limit":      self.leverage_limit,
            "vol_target_lookback": self.vol_target_lookback,
        }
        if self.vol_target is not None:
            d["vol_target"] = self.vol_target
        return d


# ---------------------------------------------------------------------------
# Strategy builder
# ---------------------------------------------------------------------------


class Strategy:
    """Strategy definition.

    Build a custom strategy using boolean expression strings and indicator
    references, or pick a pre-built template via the classmethods.

    Expressions reference indicator output columns by their ``ref`` name.
    Use :meth:`indicator` to declare which indicators your expressions need.

    .. tip::
        **Indicator library** — names, parameter schemas, output columns:
        https://api.backtest360.com/docs#tag/Reference/operation/list_indicators_api_indicators_get

        Or call ``client.list_indicators()`` at runtime.

        **Pre-built templates** — copy a template name into
        ``Strategy.<name>()`` or use ``client.list_strategies()``
        to browse the full list.

    Args:
        name: Strategy identifier string (arbitrary, used for labelling).
        long_entry: Boolean expression string that fires long entry.
            References indicator output columns by their ``ref`` name.
        long_exit: Boolean expression string that fires long exit.
        short_entry: Boolean expression for short entry (``None`` for
            long-only strategies).
        short_exit: Boolean expression for short exit.
        indicators: List of indicator descriptor dicts produced by
            :meth:`indicator`.

    Example::

        from backtest360 import Strategy

        strat = Strategy(
            name="rsi_mean_reversion",
            long_entry="rsi < 30",
            long_exit="rsi > 70",
            indicators=[Strategy.indicator("rsi", period=14)],
        )

    For a crossover strategy using transform indicators::

        strat = Strategy(
            name="sma_crossover",
            long_entry="x_above",
            long_exit="x_below",
            indicators=[
                Strategy.indicator("sma", ref="sma_10", period=10),
                Strategy.indicator("sma", ref="sma_50", period=50),
                Strategy.indicator("cross_above", ref="x_above",
                                   kind="transform", upstream=["sma_10", "sma_50"]),
                Strategy.indicator("cross_below", ref="x_below",
                                   kind="transform", upstream=["sma_10", "sma_50"]),
            ],
        )
    """

    def __init__(
        self,
        name: str,
        long_entry: str | None = None,
        long_exit: str | None = None,
        short_entry: str | None = None,
        short_exit: str | None = None,
        indicators: list[dict] | None = None,
    ) -> None:
        self.name = name
        self.long_entry = long_entry
        self.long_exit = long_exit
        self.short_entry = short_entry
        self.short_exit = short_exit
        self.indicators: list[dict] = indicators or []

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def indicator(
        name: str,
        *,
        ref: str | None = None,
        kind: str = "technical",
        upstream: list[str] | None = None,
        **params: Any,
    ) -> dict:
        """Declare an indicator reference for use in condition expressions.

        Args:
            name: Indicator name — e.g. ``"rsi"``, ``"sma"``, ``"macd"``,
                ``"cross_above"``. See the indicator library for the full list:
                https://api.backtest360.com/docs#tag/Reference/operation/list_indicators_api_indicators_get
            ref: Column name referenced in expression strings. Defaults to
                ``name`` when only one instance of that indicator is used.
                Specify a unique ``ref`` when the same indicator appears with
                different params (e.g. ``ref="rsi_fast"`` and
                ``ref="rsi_slow"``).
            kind: Indicator kind. One of ``"technical"`` (default),
                ``"transform"``, ``"model"``, ``"primitive"``.
            upstream: Refs of upstream indicators consumed by transform
                indicators (e.g. ``upstream=["sma_10", "sma_50"]``).
            **params: Indicator parameters (e.g. ``period=14``). See the
                indicator library for each indicator's parameter schema.

        Returns:
            Indicator descriptor dict suitable for passing in ``indicators=``.

        Example::

            Strategy.indicator("rsi", period=14)
            Strategy.indicator("rsi", ref="rsi_fast", period=5)
            Strategy.indicator("sma", ref="sma_200", period=200)
            Strategy.indicator(
                "cross_above", ref="x_above", kind="transform",
                upstream=["sma_10", "sma_50"],
            )
        """
        return {
            "ref":      ref if ref is not None else name,
            "name":     name,
            "kind":     kind,
            "params":   dict(params),
            "upstream": list(upstream) if upstream else [],
        }

    @staticmethod
    def _expr_to_node(expr: str | None) -> dict | None:
        """Convert a bare expression string to a json-logic leaf node."""
        if expr is None:
            return None
        return {"op": "leaf", "expr": expr}

    def to_wire(self) -> dict:
        """Serialise to the engine's ``{condition_tree, indicators}`` wire shape."""
        return {
            "condition_tree": {
                "long_entry":  self._expr_to_node(self.long_entry),
                "long_exit":   self._expr_to_node(self.long_exit),
                "short_entry": self._expr_to_node(self.short_entry),
                "short_exit":  self._expr_to_node(self.short_exit),
            },
            "indicators": self.indicators,
        }

    # ---------------------------------------------------------------------------
    # Pre-built templates (hand-synced with the engine's /api/strategies)
    # For the definitive list and parameter options, see:
    # https://api.backtest360.com/docs#tag/Reference/operation/list_strategies_api_strategies_get
    # ---------------------------------------------------------------------------

    @classmethod
    def rsi_threshold_long(cls) -> Strategy:
        """RSI threshold — long-only mean reversion (oversold entry, overbought exit).

        Indicators: RSI(14). Long-only, daily bars.
        """
        return cls(
            name="rsi_threshold_long",
            long_entry="rsi_14 < 30",
            long_exit="rsi_14 > 70",
            indicators=[cls.indicator("rsi", ref="rsi_14", period=14)],
        )

    @classmethod
    def rsi_mean_reversion(cls) -> Strategy:
        """RSI mean reversion — buy oversold, sell overbought.

        Indicators: RSI(14). Long-only, daily bars.
        """
        return cls(
            name="rsi_mean_reversion",
            long_entry="rsi_14 < 30",
            long_exit="rsi_14 > 70",
            indicators=[cls.indicator("rsi", ref="rsi_14", period=14)],
        )

    @classmethod
    def ma_crossover(cls) -> Strategy:
        """SMA(10) / SMA(50) crossover — classic trend-following.

        Indicators: SMA(10), SMA(50), CrossAbove, CrossBelow. Long-only, daily.
        """
        return cls(
            name="ma_crossover",
            long_entry="x_above",
            long_exit="x_below",
            indicators=[
                cls.indicator("sma", ref="sma_10", period=10),
                cls.indicator("sma", ref="sma_50", period=50),
                cls.indicator(
                    "cross_above", ref="x_above", kind="transform",
                    upstream=["sma_10", "sma_50"],
                ),
                cls.indicator(
                    "cross_below", ref="x_below", kind="transform",
                    upstream=["sma_10", "sma_50"],
                ),
            ],
        )

    @classmethod
    def momentum_6m_long(cls) -> Strategy:
        """Absolute 6-month momentum — long when ROC(126) > 0.

        Indicators: ROC(126). Long-only, daily bars.
        """
        return cls(
            name="momentum_6m_long",
            long_entry="roc_126 > 0",
            long_exit="roc_126 <= 0",
            indicators=[cls.indicator("roc", ref="roc_126", period=126)],
        )
