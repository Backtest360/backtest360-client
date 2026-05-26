"""Round-trip serialization tests for all input and output DTOs."""

from dataclasses import asdict

import pytest

import numpy as np
import pandas as pd

from backtest360.dtos import AssetInfo, ExecutionCosts, ExecutionMode, Indicator, MarketData, PositionSizing, RiskControls


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
