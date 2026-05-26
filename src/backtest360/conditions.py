"""Condition-tree builder helpers.

``C`` provides static factory methods that produce the engine's json-logic tree
shapes. Leaves reference Indicator ids via ``{"var": "<id>.output"}`` or
``{"var": "<id>.<col>"}`` notation.

Example::

    tree = {
        "long_entry": C.and_(C.lt("rsi_14", 30), C.gt("close", "sma_50")),
        "long_exit":  C.gt("rsi_14", 50),
        "short_entry": None,
        "short_exit":  None,
    }
"""

from __future__ import annotations

from typing import Union

# A leaf operand is either a string indicator ref or a numeric literal.
_Operand = Union[str, int, float]


def _ref(value: _Operand) -> object:
    """Wrap a string indicator id in a json-logic var node; pass numbers as-is."""
    if isinstance(value, str):
        col = value if "." in value else f"{value}.output"
        return {"var": col}
    return value


class C:
    """Static condition-tree builder.

    Every method returns a plain dict in the engine's json-logic shape.
    Methods can be freely nested — the output is just a dict.
    """

    # -------------------------------------------------------------------
    # Comparison leaves
    # -------------------------------------------------------------------

    @staticmethod
    def gt(left: _Operand, right: _Operand) -> dict:
        """left > right"""
        return {"gt": [_ref(left), _ref(right)]}

    @staticmethod
    def lt(left: _Operand, right: _Operand) -> dict:
        """left < right"""
        return {"lt": [_ref(left), _ref(right)]}

    @staticmethod
    def ge(left: _Operand, right: _Operand) -> dict:
        """left >= right"""
        return {"gte": [_ref(left), _ref(right)]}

    @staticmethod
    def le(left: _Operand, right: _Operand) -> dict:
        """left <= right"""
        return {"lte": [_ref(left), _ref(right)]}

    @staticmethod
    def eq(left: _Operand, right: _Operand) -> dict:
        """left == right"""
        return {"==": [_ref(left), _ref(right)]}

    @staticmethod
    def ne(left: _Operand, right: _Operand) -> dict:
        """left != right"""
        return {"!=": [_ref(left), _ref(right)]}

    # -------------------------------------------------------------------
    # Logical combinators
    # -------------------------------------------------------------------

    @staticmethod
    def and_(*conditions: dict) -> dict:
        """All conditions must be true."""
        return {"and": list(conditions)}

    @staticmethod
    def or_(*conditions: dict) -> dict:
        """At least one condition must be true."""
        return {"or": list(conditions)}

    @staticmethod
    def not_(condition: dict) -> dict:
        """Condition must be false."""
        return {"!": condition}

    # -------------------------------------------------------------------
    # Cross-over helpers
    # -------------------------------------------------------------------

    @staticmethod
    def cross_above(fast: _Operand, slow: _Operand) -> dict:
        """fast crosses above slow (fast > slow after being below)."""
        return {"cross_above": [_ref(fast), _ref(slow)]}

    @staticmethod
    def cross_below(fast: _Operand, slow: _Operand) -> dict:
        """fast crosses below slow (fast < slow after being above)."""
        return {"cross_below": [_ref(fast), _ref(slow)]}
