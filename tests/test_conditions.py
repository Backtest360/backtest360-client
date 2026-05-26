"""Unit tests for C condition-tree builder helpers."""

import pytest

from backtest360.conditions import C


# ---------------------------------------------------------------------------
# _ref helper (tested indirectly)
# ---------------------------------------------------------------------------

def test_gt_string_wraps_in_var():
    node = C.gt("rsi_14", 30)
    assert node == {"gt": [{"var": "rsi_14.output"}, 30]}


def test_gt_dotted_string_not_double_wrapped():
    node = C.gt("rsi_14.output", 30)
    assert node == {"gt": [{"var": "rsi_14.output"}, 30]}


def test_gt_numeric_literal_not_wrapped():
    node = C.gt(50, 30)
    assert node == {"gt": [50, 30]}


# ---------------------------------------------------------------------------
# Comparison leaves
# ---------------------------------------------------------------------------

def test_gt():
    assert C.gt("rsi", 70) == {"gt": [{"var": "rsi.output"}, 70]}


def test_lt():
    assert C.lt("rsi", 30) == {"lt": [{"var": "rsi.output"}, 30]}


def test_ge():
    assert C.ge("price", 100) == {"gte": [{"var": "price.output"}, 100]}


def test_le():
    assert C.le("price", 50.5) == {"lte": [{"var": "price.output"}, 50.5]}


def test_eq():
    assert C.eq("signal", 1) == {"==": [{"var": "signal.output"}, 1]}


def test_ne():
    assert C.ne("signal", 0) == {"!=": [{"var": "signal.output"}, 0]}


# ---------------------------------------------------------------------------
# Logical combinators
# ---------------------------------------------------------------------------

def test_and_two():
    node = C.and_(C.gt("rsi", 30), C.lt("rsi", 70))
    assert node == {
        "and": [
            {"gt": [{"var": "rsi.output"}, 30]},
            {"lt": [{"var": "rsi.output"}, 70]},
        ]
    }


def test_and_three():
    node = C.and_(C.gt("a", 1), C.gt("b", 2), C.gt("c", 3))
    assert len(node["and"]) == 3


def test_or_two():
    node = C.or_(C.lt("rsi", 30), C.gt("rsi", 70))
    assert node == {
        "or": [
            {"lt": [{"var": "rsi.output"}, 30]},
            {"gt": [{"var": "rsi.output"}, 70]},
        ]
    }


def test_not_():
    node = C.not_(C.gt("rsi", 70))
    assert node == {"!": {"gt": [{"var": "rsi.output"}, 70]}}


# ---------------------------------------------------------------------------
# Cross-over helpers
# ---------------------------------------------------------------------------

def test_cross_above():
    node = C.cross_above("fast_sma", "slow_sma")
    assert node == {"cross_above": [{"var": "fast_sma.output"}, {"var": "slow_sma.output"}]}


def test_cross_below():
    node = C.cross_below("fast_sma", "slow_sma")
    assert node == {"cross_below": [{"var": "fast_sma.output"}, {"var": "slow_sma.output"}]}


# ---------------------------------------------------------------------------
# Nesting
# ---------------------------------------------------------------------------

def test_nested_and_or():
    node = C.and_(
        C.or_(C.lt("rsi", 30), C.gt("rsi", 70)),
        C.gt("close", "sma_200"),
    )
    assert "and" in node
    assert "or" in node["and"][0]


def test_plan_example():
    """The plan's example: C.and_(C.gt("rsi", 70), C.lt("close", "sma_50")).to_dict()
    is not quite right — C.and_ returns a dict, not an object with to_dict().
    Verify the shape is the engine's json-logic shape."""
    node = C.and_(C.gt("rsi", 70), C.lt("close", "sma_50"))
    assert node["and"][0] == {"gt": [{"var": "rsi.output"}, 70]}
    assert node["and"][1] == {"lt": [{"var": "close.output"}, {"var": "sma_50.output"}]}
