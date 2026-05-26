"""Round-trip serialization tests for all input and output DTOs."""

from dataclasses import asdict

import pytest

import numpy as np
import pandas as pd

from backtest360.dtos import (
    AssetInfo,
    BacktestConfig,
    BadDataEntry,
    BadDataReport,
    ExecutionCosts,
    ExecutionMode,
    Indicator,
    MarketData,
    OffAnchorEvent,
    OffAnchorReport,
    PositionSizing,
    RiskControls,
    Strategy,
    Trade,
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
    ec = ExecutionCosts(slippage_bps=5.0, fee_pct=0.001, vol_scaled_slippage=True, vol_slippage_lookback=30)
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
    ps = PositionSizing(position_weight=0.5, vol_target=0.15, vol_target_lookback=60, leverage_limit=2.0)
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
    ai = AssetInfo(ticker="SPY", name="SPDR S&P 500 ETF", asset_class="stocks",
                   exchange="NYSE", currency="USD", active=True)
    d = ai.to_dict()
    assert d == {
        "ticker": "SPY", "name": "SPDR S&P 500 ETF", "asset_class": "stocks",
        "exchange": "NYSE", "currency": "USD", "active": True,
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
    return pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5, "close": c, "volume": 1000.0}, index=idx)


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


def test_market_data_load_not_yet_implemented():
    """load() is a stub until step 3.7."""
    md = MarketData()
    df = _make_ohlcv()
    with pytest.raises(NotImplementedError):
        md.load(df)


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
        entry_bar=5, entry_date="2024-01-08T00:00:00+00:00", direction=1,
        entry_price=101.0, exit_bar=10, exit_date="2024-01-15T00:00:00+00:00",
        exit_price=105.0, exit_reason="exit_signal", holding_bars=5,
        return_gross=0.038, return_net=0.035, cumulative_pnl=0.035,
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
        bar_idx=7, anchor="open", target_hour=9.5,
        timestamp="2024-01-08T09:30:00+00:00", chosen_idx=0,
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
