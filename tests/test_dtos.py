"""Round-trip serialization tests for all input and output DTOs."""

from dataclasses import asdict

import pytest

from backtest360.dtos import ExecutionCosts, ExecutionMode, RiskControls


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
