"""Condition-tree builder helpers.

``C`` produces the engine's ``op/expr`` tree format. Comparison leaves become
pandas-eval strings; logical nodes use ``op=and|or|not`` with an ``args`` list.

Example::

    tree = {
        "long_entry": C.and_(C.lt("rsi", 30), C.gt("close", "sma_200")),
        "long_exit":  C.gt("rsi", 70),
        "short_entry": None,
        "short_exit":  None,
    }

Cross-over conditions reference a ``cross_above`` or ``cross_below`` transform
indicator by its id::

    indicators = [
        Indicator(id="sma_fast", name="sma", params={"period": 10}, upstream=[]),
        Indicator(id="sma_slow", name="sma", params={"period": 50}, upstream=[]),
        Indicator(id="x_above", name="cross_above", params={}, upstream=["sma_fast", "sma_slow"]),
    ]
    long_entry = C.cross_above("x_above")   # checks x_above > 0
"""

from __future__ import annotations

_Operand = str | int | float

_OPS = {"gt": ">", "lt": "<", "ge": ">=", "le": "<=", "eq": "==", "ne": "!="}


def _expr_side(value: _Operand) -> str:
    """Convert an operand to a pandas-eval token."""
    if isinstance(value, str):
        return value
    return repr(value)


def _leaf(left: _Operand, op: str, right: _Operand) -> dict:
    return {"op": "leaf", "expr": f"{_expr_side(left)} {op} {_expr_side(right)}"}


class C:
    """Static condition-tree builder.

    Every method returns a plain dict in the engine's ``op/expr`` tree shape.
    Methods can be freely nested — the output is just a dict.
    """

    # -------------------------------------------------------------------
    # Comparison leaves — produce {"op": "leaf", "expr": "..."}
    # -------------------------------------------------------------------

    @staticmethod
    def gt(left: _Operand, right: _Operand) -> dict:
        """left > right"""
        return _leaf(left, ">", right)

    @staticmethod
    def lt(left: _Operand, right: _Operand) -> dict:
        """left < right"""
        return _leaf(left, "<", right)

    @staticmethod
    def ge(left: _Operand, right: _Operand) -> dict:
        """left >= right"""
        return _leaf(left, ">=", right)

    @staticmethod
    def le(left: _Operand, right: _Operand) -> dict:
        """left <= right"""
        return _leaf(left, "<=", right)

    @staticmethod
    def eq(left: _Operand, right: _Operand) -> dict:
        """left == right"""
        return _leaf(left, "==", right)

    @staticmethod
    def ne(left: _Operand, right: _Operand) -> dict:
        """left != right"""
        return _leaf(left, "!=", right)

    # -------------------------------------------------------------------
    # Logical combinators — produce {"op": "and"|"or"|"not", "args": [...]}
    # -------------------------------------------------------------------

    @staticmethod
    def and_(*conditions: dict) -> dict:
        """All conditions must be true."""
        return {"op": "and", "args": list(conditions)}

    @staticmethod
    def or_(*conditions: dict) -> dict:
        """At least one condition must be true."""
        return {"op": "or", "args": list(conditions)}

    @staticmethod
    def not_(condition: dict) -> dict:
        """Condition must be false."""
        return {"op": "not", "args": [condition]}

    # -------------------------------------------------------------------
    # Cross-over helpers
    # Cross-overs are expressed via transform indicators in the engine.
    # Pass the *id* of a cross_above / cross_below transform indicator;
    # C checks that the indicator's output fired (> 0).
    # -------------------------------------------------------------------

    @staticmethod
    def cross_above(indicator_id: str) -> dict:
        """indicator_id > 0 — fires on the bar the cross_above indicator fired.

        indicator_id must be the ``id`` of a ``cross_above`` transform
        indicator already declared in ``Strategy.indicators``.
        """
        return {"op": "leaf", "expr": f"{indicator_id} > 0"}

    @staticmethod
    def cross_below(indicator_id: str) -> dict:
        """indicator_id > 0 — fires on the bar the cross_below indicator fired.

        indicator_id must be the ``id`` of a ``cross_below`` transform
        indicator already declared in ``Strategy.indicators``.
        """
        return {"op": "leaf", "expr": f"{indicator_id} > 0"}
