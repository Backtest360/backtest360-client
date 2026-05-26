"""Round-trip serialization tests for all input and output DTOs."""

from dataclasses import asdict

import pytest

from backtest360.dtos import ExecutionCosts, ExecutionMode


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
