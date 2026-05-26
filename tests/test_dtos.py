"""Round-trip serialization tests for all input and output DTOs."""

from dataclasses import asdict

import numpy as np
import pandas as pd
import pytest

from backtest360.dtos import (
    AssetInfo,
    BacktestConfig,
    BacktestResult,
    BadDataEntry,
    BadDataReport,
    ExecutionCosts,
    ExecutionMode,
    Indicator,
    LatestSignalResult,
    MarketData,
    OffAnchorEvent,
    OffAnchorReport,
    PositionSizing,
    RiskControls,
    RunResult,
    SignalResult,
    Statistics,
    Strategy,
    Trade,
    ValidationIssue,
    ValidationResult,
)

# ---------------------------------------------------------------------------
# ExecutionMode
# ---------------------------------------------------------------------------


def test_execution_mode_defaults():
    em = ExecutionMode()
    assert em.anchor == "open"
    assert em.window == 0
    assert em.fill == "exact"


def test_execution_mode_round_trip():
    em = ExecutionMode(anchor="close", window=-2, fill="tp")
    d = em.to_dict()
    assert d == {"anchor": "close", "window": -2, "fill": "tp"}
    em2 = ExecutionMode.from_dict(d)
    assert em2 == em


def test_execution_mode_asdict():
    em = ExecutionMode(anchor="open", window=0, fill="exact")
    assert asdict(em) == {"anchor": "open", "window": 0, "fill": "exact"}


# ---------------------------------------------------------------------------
# ExecutionCosts
# ---------------------------------------------------------------------------


def test_execution_costs_defaults():
    ec = ExecutionCosts()
    assert ec.slippage_bps == 0.0
    assert ec.fee_pct == 0.0
    assert ec.vol_scaled_slippage is False
    assert ec.vol_slippage_lookback == 20


def test_execution_costs_round_trip():
    ec = ExecutionCosts(
        slippage_bps=5.0, fee_pct=0.001, vol_scaled_slippage=True, vol_slippage_lookback=30
    )
    d = ec.to_dict()
    assert d == {
        "slippage_bps": 5.0,
        "fee_pct": 0.001,
        "vol_scaled_slippage": True,
        "vol_slippage_lookback": 30,
    }
    ec2 = ExecutionCosts.from_dict(d)
    assert ec2 == ec


# ---------------------------------------------------------------------------
# RiskControls
# ---------------------------------------------------------------------------


def test_risk_controls_defaults():
    rc = RiskControls()
    assert rc.stop_type is None
    assert rc.stop_value is None
    assert rc.stop_atr_period == 14
    assert rc.stop_reentry == "immediate"
    assert rc.stop_cooldown_bars == 0
    assert rc.max_drawdown_limit is None


def test_risk_controls_round_trip():
    rc = RiskControls(
        stop_type="trailing_atr",
        stop_value=2.0,
        stop_atr_period=20,
        stop_reentry="cooldown",
        stop_cooldown_bars=3,
        max_drawdown_limit=0.15,
    )
    d = rc.to_dict()
    assert d["stop_type"] == "trailing_atr"
    assert d["max_drawdown_limit"] == 0.15
    rc2 = RiskControls.from_dict(d)
    assert rc2 == rc


def test_risk_controls_none_fields_serialize():
    rc = RiskControls()
    d = rc.to_dict()
    assert d["stop_type"] is None
    assert d["stop_value"] is None
    assert d["max_drawdown_limit"] is None


# ---------------------------------------------------------------------------
# PositionSizing
# ---------------------------------------------------------------------------


def test_position_sizing_defaults():
    ps = PositionSizing()
    assert ps.position_weight == 1.0
    assert ps.vol_target is None
    assert ps.vol_target_lookback == 20
    assert ps.leverage_limit is None


def test_position_sizing_round_trip():
    ps = PositionSizing(
        position_weight=0.5, vol_target=0.15, vol_target_lookback=60, leverage_limit=2.0
    )
    d = ps.to_dict()
    assert d == {
        "position_weight": 0.5,
        "vol_target": 0.15,
        "vol_target_lookback": 60,
        "leverage_limit": 2.0,
    }
    ps2 = PositionSizing.from_dict(d)
    assert ps2 == ps


# ---------------------------------------------------------------------------
# AssetInfo
# ---------------------------------------------------------------------------


def test_asset_info_defaults():
    ai = AssetInfo()
    assert ai.ticker == "UNKNOWN"
    assert ai.name == "UNKNOWN"
    assert ai.asset_class == "UNKNOWN"
    assert ai.exchange == "UNKNOWN"
    assert ai.currency == "UNKNOWN"
    assert ai.active is True


def test_asset_info_round_trip():
    ai = AssetInfo(
        ticker="SPY",
        name="SPDR S&P 500 ETF",
        asset_class="stocks",
        exchange="NYSE",
        currency="USD",
        active=True,
    )
    d = ai.to_dict()
    assert d == {
        "ticker": "SPY",
        "name": "SPDR S&P 500 ETF",
        "asset_class": "stocks",
        "exchange": "NYSE",
        "currency": "USD",
        "active": True,
    }
    ai2 = AssetInfo.from_dict(d)
    assert ai2 == ai


def test_asset_info_bare_constructor_is_legal():
    """Tier-A customers (BYO data) never need to pass AssetInfo."""
    ai = AssetInfo()
    d = ai.to_dict()
    ai2 = AssetInfo.from_dict(d)
    assert ai2 == ai


# ---------------------------------------------------------------------------
# MarketData
# ---------------------------------------------------------------------------


def _make_ohlcv(n: int = 10) -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=n, freq="B", tz="UTC")
    c = 100.0 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {"open": c, "high": c + 0.5, "low": c - 0.5, "close": c, "volume": 1000.0}, index=idx
    )


def test_market_data_bare_constructor():
    md = MarketData()
    assert md.ohlcv is None
    assert isinstance(md.asset_info, AssetInfo)
    assert md.is_24h is None
    assert md.bar_frequency is None
    assert md.missing_bars == 0
    assert md.bad_prices == 0
    assert md.quality_warnings == []


def test_market_data_ts_alias():
    df = _make_ohlcv()
    md = MarketData()
    md.ts = df
    assert md.ohlcv is df
    assert md.ts is df


def test_market_data_ohlcv_field():
    df = _make_ohlcv()
    md = MarketData(ohlcv=df)
    assert md.ts is df


def test_market_data_scalar_fields_round_trip():
    """Round-trip for all non-DataFrame fields."""
    md = MarketData(
        asset_info=AssetInfo(ticker="SPY"),
        is_24h=False,
        session_open=9.5,
        session_close=16.0,
        trading_days_per_year=252,
        bar_frequency="daily",
        source_bars_per_year=252,
        missing_bars=2,
        bad_prices=0,
        quality_warnings=["sparse"],
    )
    assert md.is_24h is False
    assert md.session_open == 9.5
    assert md.trading_days_per_year == 252
    assert md.asset_info.ticker == "SPY"
    assert md.quality_warnings == ["sparse"]


def test_market_data_load_populates_bar_frequency():
    """load() detects daily frequency from daily-spaced fixture."""
    df = _make_ohlcv(252)  # a year of daily bars
    md = MarketData()
    md.load(df)
    assert md.bar_frequency == "daily"
    assert md.ohlcv is df


def test_market_data_load_populates_is_24h_for_weekday_data():
    """load() detects session market (no weekend bars)."""
    df = _make_ohlcv(252)
    md = MarketData()
    md.load(df)
    # 252 business-day bars → no weekend bars → session market
    assert md.is_24h is False


def test_market_data_load_populates_market_hours():
    """load() sets session_open and session_close on session markets."""
    df = _make_ohlcv(252)
    md = MarketData()
    md.load(df)
    if not md.is_24h:
        assert md.session_open is not None
        assert md.session_close is not None
    else:
        assert md.session_open == 0.0


def test_market_data_load_chaining():
    """load() returns self for chaining."""
    df = _make_ohlcv(252)
    md = MarketData()
    result = md.load(df)
    assert result is md


def test_market_data_load_hourly_fixture():
    """load() detects hourly frequency from hourly-spaced data."""
    idx = pd.date_range("2024-01-02", periods=1000, freq="h", tz="UTC")
    c = 100.0 + np.arange(1000, dtype=float) * 0.01
    df = pd.DataFrame(
        {"open": c, "high": c + 0.5, "low": c - 0.5, "close": c, "volume": 1000.0}, index=idx
    )
    md = MarketData()
    md.load(df)
    assert md.bar_frequency == "hourly"
    assert md.missing_bars == 0
    assert md.bad_prices == 0


def test_market_data_load_bad_prices_detected():
    """load() flags NaN prices in quality_warnings."""
    df = _make_ohlcv(252)
    df.loc[df.index[5], "close"] = float("nan")
    md = MarketData()
    md.load(df)
    assert md.bad_prices >= 1
    assert any("bad price" in w for w in md.quality_warnings)


# ---------------------------------------------------------------------------
# Indicator
# ---------------------------------------------------------------------------


def test_indicator_defaults():
    ind = Indicator()
    assert ind.id == ""
    assert ind.name == ""
    assert ind.params == {}
    assert ind.upstream == []


def test_indicator_round_trip():
    ind = Indicator(id="rsi_14", name="RSI", params={"lookback": 14}, upstream=[])
    d = ind.to_dict()
    assert d == {"id": "rsi_14", "name": "RSI", "params": {"lookback": 14}, "upstream": []}
    ind2 = Indicator.from_dict(d)
    assert ind2 == ind


def test_indicator_with_upstream():
    ind = Indicator(id="zscore_rsi", name="ZScore", params={"lookback": 20}, upstream=["rsi_14"])
    d = ind.to_dict()
    assert d["upstream"] == ["rsi_14"]
    ind2 = Indicator.from_dict(d)
    assert ind2.upstream == ["rsi_14"]


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------


def _make_strategy() -> Strategy:
    ind = Indicator(id="rsi_14", name="RSI", params={"lookback": 14})
    tree = {
        "long_entry": {"gt": [{"var": "rsi_14.output"}, 30]},
        "long_exit": {"lt": [{"var": "rsi_14.output"}, 50]},
        "short_entry": None,
        "short_exit": None,
    }
    return Strategy(
        name="RSI threshold long",
        description="Go long when RSI < 30, exit when RSI > 50.",
        condition_tree=tree,
        indicators=[ind],
        requires={"rsi_lookback": {"type": "int", "min": 2}},
        defaults={"rsi_lookback": 14},
        locked_params=["rsi_lookback"],
        tier="customer",
    )


def test_strategy_defaults():
    s = Strategy()
    assert s.name == ""
    assert s.condition_tree is None
    assert s.indicators == []
    assert s.precomputed_signals is None
    assert s.tier == "customer"
    assert s.locked_params == []


def test_strategy_round_trip():
    s = _make_strategy()
    d = s.to_dict()
    assert d["name"] == "RSI threshold long"
    assert d["condition_tree"]["long_entry"] == {"gt": [{"var": "rsi_14.output"}, 30]}
    assert len(d["indicators"]) == 1
    assert d["indicators"][0]["name"] == "RSI"
    assert d["locked_params"] == ["rsi_lookback"]
    s2 = Strategy.from_dict(d)
    assert s2.name == s.name
    assert isinstance(s2.indicators[0], Indicator)
    assert s2.indicators[0].name == "RSI"
    assert s2.locked_params == ["rsi_lookback"]


def test_strategy_precomputed_signals_not_in_to_dict():
    """precomputed_signals is excluded from to_dict (handled separately by client)."""
    import pandas as pd

    signals = pd.Series([0, 1, 1, -1, 0], dtype=int)
    s = Strategy(precomputed_signals=signals)
    d = s.to_dict()
    assert "precomputed_signals" not in d


def test_strategy_from_dict_handles_indicator_dicts():
    d = {
        "name": "test",
        "indicators": [{"id": "sma_10", "name": "SMA", "params": {"lookback": 10}, "upstream": []}],
    }
    s = Strategy.from_dict(d)
    assert isinstance(s.indicators[0], Indicator)
    assert s.indicators[0].id == "sma_10"


# ---------------------------------------------------------------------------
# BacktestConfig
# ---------------------------------------------------------------------------


def test_backtest_config_defaults():
    bc = BacktestConfig()
    assert bc.signal_frequency == "daily"
    assert bc.entry_mode is None
    assert bc.exit_mode is None
    assert bc.costs is None
    assert bc.risk is None
    assert bc.sizing is None
    assert bc.strict_anchors is False
    assert bc.risk_free_rate == 0.0
    assert bc.on_bad_data == "raise"
    assert bc.random_seed == 42
    assert bc.include_per_bar_df is False
    assert bc.include_indicator_values is False


def test_backtest_config_round_trip_all_none():
    bc = BacktestConfig()
    d = bc.to_dict()
    assert d["signal_frequency"] == "daily"
    assert d["entry_mode"] is None
    assert d["costs"] is None
    bc2 = BacktestConfig.from_dict(d)
    assert bc2.signal_frequency == "daily"
    assert bc2.entry_mode is None
    assert bc2.costs is None


def test_backtest_config_round_trip_nested():
    bc = BacktestConfig(
        signal_frequency="hourly",
        entry_mode=ExecutionMode(anchor="open", window=0, fill="exact"),
        exit_mode=ExecutionMode(anchor="close", window=0, fill="exact"),
        costs=ExecutionCosts(slippage_bps=2.0, fee_pct=0.0005),
        risk=RiskControls(stop_type="fixed", stop_value=0.02),
        sizing=PositionSizing(position_weight=0.5),
        risk_free_rate=0.04,
        include_per_bar_df=True,
    )
    d = bc.to_dict()
    assert d["entry_mode"]["anchor"] == "open"
    assert d["costs"]["slippage_bps"] == 2.0
    assert d["risk"]["stop_type"] == "fixed"
    assert d["sizing"]["position_weight"] == 0.5
    bc2 = BacktestConfig.from_dict(d)
    assert isinstance(bc2.entry_mode, ExecutionMode)
    assert bc2.entry_mode.anchor == "open"
    assert isinstance(bc2.costs, ExecutionCosts)
    assert bc2.costs.slippage_bps == 2.0
    assert isinstance(bc2.risk, RiskControls)
    assert bc2.risk.stop_type == "fixed"
    assert bc2.include_per_bar_df is True


def test_backtest_config_has_no_strategy_field():
    """Strategy is not a field on BacktestConfig — it's passed to backtest() separately."""
    assert not hasattr(BacktestConfig, "strategy")


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------


def test_trade_defaults():
    t = Trade()
    assert t.entry_bar == 0
    assert t.direction == 0
    assert t.exit_reason == ""
    assert t.cumulative_pnl == 0.0


def test_trade_round_trip():
    t = Trade(
        entry_bar=5,
        entry_date="2024-01-08T00:00:00+00:00",
        direction=1,
        entry_price=101.0,
        exit_bar=10,
        exit_date="2024-01-15T00:00:00+00:00",
        exit_price=105.0,
        exit_reason="exit_signal",
        holding_bars=5,
        return_gross=0.038,
        return_net=0.035,
        cumulative_pnl=0.035,
    )
    d = t.to_dict()
    assert d["direction"] == 1
    assert d["exit_reason"] == "exit_signal"
    t2 = Trade.from_dict(d)
    assert t2 == t


# ---------------------------------------------------------------------------
# BadDataEntry
# ---------------------------------------------------------------------------


def test_bad_data_entry_round_trip():
    bde = BadDataEntry(bar_index=42, bar_state="HOLD", reason="start=nan")
    d = bde.to_dict()
    assert d == {"bar_index": 42, "bar_state": "HOLD", "reason": "start=nan"}
    bde2 = BadDataEntry.from_dict(d)
    assert bde2 == bde


# ---------------------------------------------------------------------------
# OffAnchorEvent
# ---------------------------------------------------------------------------


def test_off_anchor_event_round_trip():
    ev = OffAnchorEvent(
        bar_idx=7,
        anchor="open",
        target_hour=9.5,
        timestamp="2024-01-08T09:30:00+00:00",
        chosen_idx=0,
    )
    d = ev.to_dict()
    assert d["anchor"] == "open"
    ev2 = OffAnchorEvent.from_dict(d)
    assert ev2 == ev


# ---------------------------------------------------------------------------
# BadDataReport
# ---------------------------------------------------------------------------


def test_bad_data_report_empty():
    r = BadDataReport()
    assert r.count == 0
    assert r.entries == []
    assert r.policy == ""


def test_bad_data_report_round_trip():
    bde = BadDataEntry(bar_index=3, bar_state="HOLD", reason="end=-1.0")
    r = BadDataReport(count=1, entries=[bde], policy="zero")
    d = r.to_dict()
    assert d["count"] == 1
    assert d["entries"][0]["bar_index"] == 3
    r2 = BadDataReport.from_dict(d)
    assert r2.count == 1
    assert isinstance(r2.entries[0], BadDataEntry)
    assert r2.entries[0].reason == "end=-1.0"


# ---------------------------------------------------------------------------
# OffAnchorReport
# ---------------------------------------------------------------------------


def test_off_anchor_report_empty():
    r = OffAnchorReport()
    assert r.open_count == 0
    assert r.close_count == 0
    assert r.events == []


def test_off_anchor_report_round_trip():
    ev = OffAnchorEvent(bar_idx=2, anchor="close", target_hour=16.0, chosen_idx=5)
    r = OffAnchorReport(open_count=0, close_count=1, events=[ev], strict=False)
    d = r.to_dict()
    assert d["close_count"] == 1
    r2 = OffAnchorReport.from_dict(d)
    assert r2.close_count == 1
    assert isinstance(r2.events[0], OffAnchorEvent)
    assert r2.events[0].anchor == "close"


# ---------------------------------------------------------------------------
# SignalResult
# ---------------------------------------------------------------------------


def test_signal_result_defaults():
    sr = SignalResult()
    assert sr.long_entry_fired is None
    assert sr.long_exit_fired is None


def test_signal_result_from_dict():
    d = {
        "long_entry_fired": [True, False, True],
        "long_exit_fired": [False, True, False],
        "short_entry_fired": None,
        "short_exit_fired": None,
    }
    sr = SignalResult.from_dict(d)
    assert sr.long_entry_fired is not None
    assert sr.long_entry_fired.tolist() == [True, False, True]
    assert bool(sr.long_exit_fired.iloc[1]) is True
    assert sr.short_entry_fired is None


def test_signal_result_from_dict_all_none():
    sr = SignalResult.from_dict({})
    assert sr.long_entry_fired is None
    assert sr.short_exit_fired is None


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def test_statistics_all_defaults_none():
    s = Statistics()
    assert s.sharpe_ratio is None
    assert s.cagr is None
    assert s.max_drawdown is None
    assert s.beta is None  # benchmark metric


def test_statistics_round_trip_scalars():
    s = Statistics(
        total_return=0.25,
        cagr=0.18,
        sharpe_ratio=1.42,
        sortino_ratio=2.1,
        max_drawdown=-0.12,
        calmar_ratio=1.5,
        total_trades=24,
        win_rate=0.58,
    )
    d = s.to_dict()
    assert d["sharpe_ratio"] == 1.42
    assert d["total_trades"] == 24
    assert d["beta"] is None
    s2 = Statistics.from_dict(d)
    assert s2.sharpe_ratio == 1.42
    assert s2.total_trades == 24
    assert s2.beta is None


def test_statistics_from_dict_ignores_unknown_keys():
    """Additive-only contract: unknown server keys are silently ignored."""
    d = {"sharpe_ratio": 1.1, "future_metric_not_in_sdk": 42.0}
    s = Statistics.from_dict(d)
    assert s.sharpe_ratio == 1.1
    assert not hasattr(s, "future_metric_not_in_sdk")


def test_statistics_benchmark_fields_default_none():
    s = Statistics(sharpe_ratio=1.0)
    assert s.alpha is None
    assert s.beta is None
    assert s.up_capture is None
    assert s.capture_ratio is None


def test_statistics_field_count():
    """Verify we have at least 120 fields (the plan's stated count)."""
    import dataclasses

    fields = dataclasses.fields(Statistics)
    assert len(fields) >= 120, f"Expected >= 120 fields, got {len(fields)}"


# ---------------------------------------------------------------------------
# RunResult
# ---------------------------------------------------------------------------


def test_run_result_defaults():
    rr = RunResult()
    assert rr.trades == []
    assert rr.signal_bars_per_year is None
    assert rr.returns is None
    assert rr.bad_data is None


def test_run_result_from_dict_minimal():
    d = {
        "trades": [
            {
                "entry_bar": 0,
                "entry_date": None,
                "direction": 1,
                "entry_price": 100.0,
                "exit_bar": 5,
                "exit_date": None,
                "exit_price": 105.0,
                "exit_reason": "exit_signal",
                "holding_bars": 5,
                "return_gross": 0.05,
                "return_net": 0.048,
                "cumulative_pnl": 0.048,
            }
        ],
        "signal_bars_per_year": 252,
    }
    rr = RunResult.from_dict(d)
    assert len(rr.trades) == 1
    assert isinstance(rr.trades[0], Trade)
    assert rr.trades[0].direction == 1
    assert rr.signal_bars_per_year == 252
    assert rr.returns is None  # not included without include_per_bar_df


def test_run_result_from_dict_with_series():
    d = {
        "trades": [],
        "signal_bars_per_year": 52,
        "returns": [0.01, -0.02, 0.03],
        "equity": [1.01, 0.99, 1.02],
    }
    rr = RunResult.from_dict(d)
    assert rr.returns is not None
    assert len(rr.returns) == 3
    assert rr.equity.iloc[2] == pytest.approx(1.02)


# ---------------------------------------------------------------------------
# BacktestResult
# ---------------------------------------------------------------------------


def test_backtest_result_defaults():
    br = BacktestResult()
    assert br.run_result is None
    assert br.statistics is None
    assert br.signal_result is None


def test_backtest_result_from_dict():
    d = {
        "run_result": {
            "trades": [],
            "signal_bars_per_year": 252,
        },
        "stats": {
            "sharpe_ratio": 1.35,
            "total_return": 0.42,
        },
    }
    br = BacktestResult.from_dict(d)
    assert isinstance(br.run_result, RunResult)
    assert isinstance(br.statistics, Statistics)
    assert br.statistics.sharpe_ratio == pytest.approx(1.35)
    assert br.signal_result is None  # no signal_diagnostics key


def test_backtest_result_with_signal_diagnostics():
    d = {
        "run_result": {"trades": [], "signal_bars_per_year": 252},
        "stats": {},
        "signal_diagnostics": {
            "long_entry_fired": [True, False],
            "long_exit_fired": [False, True],
            "short_entry_fired": None,
            "short_exit_fired": None,
        },
    }
    br = BacktestResult.from_dict(d)
    assert br.signal_result is not None
    assert isinstance(br.signal_result, SignalResult)
    assert br.signal_result.long_entry_fired is not None


# ---------------------------------------------------------------------------
# ValidationIssue
# ---------------------------------------------------------------------------


def test_validation_issue_defaults():
    vi = ValidationIssue()
    assert vi.code == ""
    assert vi.message == ""
    assert vi.field is None


def test_validation_issue_round_trip():
    vi = ValidationIssue(
        code="INVALID_LOOKBACK",
        message="RSI lookback must be > 0",
        field="indicators[0].params.lookback",
    )
    d = vi.to_dict()
    assert d["code"] == "INVALID_LOOKBACK"
    vi2 = ValidationIssue.from_dict(d)
    assert vi2 == vi


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


def test_validation_result_valid():
    vr = ValidationResult(valid=True, issues=[])
    d = vr.to_dict()
    assert d["valid"] is True
    assert d["issues"] == []
    vr2 = ValidationResult.from_dict(d)
    assert vr2.valid is True


def test_validation_result_invalid_round_trip():
    vi = ValidationIssue(code="ERR", message="bad", field="x")
    vr = ValidationResult(valid=False, issues=[vi])
    d = vr.to_dict()
    vr2 = ValidationResult.from_dict(d)
    assert vr2.valid is False
    assert len(vr2.issues) == 1
    assert isinstance(vr2.issues[0], ValidationIssue)
    assert vr2.issues[0].code == "ERR"


# ---------------------------------------------------------------------------
# LatestSignalResult
# ---------------------------------------------------------------------------


def test_latest_signal_result_defaults():
    ls = LatestSignalResult()
    assert ls.signal == 0
    assert ls.bar_timestamp is None
    assert ls.warmup_bars_used is None


def test_latest_signal_result_round_trip():
    ls = LatestSignalResult(
        signal=1,
        bar_timestamp="2024-06-01T00:00:00+00:00",
        long_entry_fired=True,
        long_exit_fired=False,
        short_entry_fired=False,
        short_exit_fired=False,
        warmup_bars_used=14,
        created_at="2024-06-01T10:00:00+00:00",
    )
    d = ls.to_dict()
    assert d["signal"] == 1
    assert d["warmup_bars_used"] == 14
    ls2 = LatestSignalResult.from_dict(d)
    assert ls2.signal == 1
    assert ls2.long_entry_fired is True
    assert ls2.warmup_bars_used == 14
