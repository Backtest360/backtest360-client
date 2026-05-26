"""Unit tests for C condition-tree builder helpers."""

from backtest360.conditions import C

# ---------------------------------------------------------------------------
# Comparison leaves — op/expr format
# ---------------------------------------------------------------------------


def test_gt():
    assert C.gt("rsi", 70) == {"op": "leaf", "expr": "rsi > 70"}


def test_lt():
    assert C.lt("rsi", 30) == {"op": "leaf", "expr": "rsi < 30"}


def test_ge():
    assert C.ge("price", 100) == {"op": "leaf", "expr": "price >= 100"}


def test_le():
    assert C.le("price", 50.5) == {"op": "leaf", "expr": "price <= 50.5"}


def test_eq():
    assert C.eq("signal", 1) == {"op": "leaf", "expr": "signal == 1"}


def test_ne():
    assert C.ne("signal", 0) == {"op": "leaf", "expr": "signal != 0"}


def test_string_right_operand():
    node = C.gt("close", "sma_200")
    assert node == {"op": "leaf", "expr": "close > sma_200"}


def test_numeric_left_operand():
    node = C.lt(30, "rsi")
    assert node == {"op": "leaf", "expr": "30 < rsi"}


def test_float_operand():
    node = C.gt("rsi", 29.5)
    assert node["expr"] == "rsi > 29.5"


# ---------------------------------------------------------------------------
# Logical combinators — op/args format
# ---------------------------------------------------------------------------


def test_and_two():
    node = C.and_(C.gt("rsi", 30), C.lt("rsi", 70))
    assert node == {
        "op": "and",
        "args": [
            {"op": "leaf", "expr": "rsi > 30"},
            {"op": "leaf", "expr": "rsi < 70"},
        ],
    }


def test_and_three():
    node = C.and_(C.gt("a", 1), C.gt("b", 2), C.gt("c", 3))
    assert node["op"] == "and"
    assert len(node["args"]) == 3


def test_or_two():
    node = C.or_(C.lt("rsi", 30), C.gt("rsi", 70))
    assert node == {
        "op": "or",
        "args": [
            {"op": "leaf", "expr": "rsi < 30"},
            {"op": "leaf", "expr": "rsi > 70"},
        ],
    }


def test_not_():
    node = C.not_(C.gt("rsi", 70))
    assert node == {"op": "not", "args": [{"op": "leaf", "expr": "rsi > 70"}]}


# ---------------------------------------------------------------------------
# Cross-over helpers — single indicator_id arg
# ---------------------------------------------------------------------------


def test_cross_above():
    node = C.cross_above("x_above")
    assert node == {"op": "leaf", "expr": "x_above > 0"}


def test_cross_below():
    node = C.cross_below("x_below")
    assert node == {"op": "leaf", "expr": "x_below > 0"}


# ---------------------------------------------------------------------------
# Nesting
# ---------------------------------------------------------------------------


def test_nested_and_or():
    node = C.and_(
        C.or_(C.lt("rsi", 30), C.gt("rsi", 70)),
        C.gt("close", "sma_200"),
    )
    assert node["op"] == "and"
    assert node["args"][0]["op"] == "or"
    assert node["args"][1] == {"op": "leaf", "expr": "close > sma_200"}


def test_full_tree_shape():
    tree = {
        "long_entry": C.and_(C.gt("rsi", 70), C.lt("close", "sma_50")),
        "long_exit": C.lt("rsi", 30),
        "short_entry": None,
        "short_exit": None,
    }
    assert tree["long_entry"]["op"] == "and"
    assert tree["long_entry"]["args"][0] == {"op": "leaf", "expr": "rsi > 70"}
    assert tree["long_entry"]["args"][1] == {"op": "leaf", "expr": "close < sma_50"}
    assert tree["long_exit"] == {"op": "leaf", "expr": "rsi < 30"}
    assert tree["short_entry"] is None
