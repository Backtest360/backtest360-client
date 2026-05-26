"""Round-trip serialization tests for all input and output DTOs."""

from dataclasses import asdict

import pytest

from backtest360.dtos import ExecutionMode


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
