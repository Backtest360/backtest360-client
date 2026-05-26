"""Unit tests for the 4 starter strategy templates."""

import pytest

from backtest360.dtos import Indicator, Strategy
from backtest360.strategies import (
    buy_and_hold,
    donchian_breakout,
    rsi_threshold_long,
    sma_crossover,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_valid_strategy(s: Strategy) -> None:
    assert isinstance(s, Strategy)
    assert s.name
    assert s.description
    assert s.condition_tree is not None or s.precomputed_signals is not None
    d = s.to_dict()
    assert d["name"] == s.name


def _assert_long_only(s: Strategy) -> None:
    ct = s.condition_tree
    assert ct is not None
    assert ct["long_entry"] is not None
    assert ct["short_entry"] is None
    assert ct["short_exit"] is None


# ---------------------------------------------------------------------------
# rsi_threshold_long
# ---------------------------------------------------------------------------

class TestRsiThresholdLong:
    def test_returns_strategy(self):
        _assert_valid_strategy(rsi_threshold_long())

    def test_long_only(self):
        _assert_long_only(rsi_threshold_long())

    def test_has_one_rsi_indicator(self):
        s = rsi_threshold_long()
        assert len(s.indicators) == 1
        ind = s.indicators[0]
        assert isinstance(ind, Indicator)
        assert ind.name == "rsi"

    def test_default_params_in_condition(self):
        s = rsi_threshold_long()
        entry_expr = s.condition_tree["long_entry"]["expr"]
        exit_expr = s.condition_tree["long_exit"]["expr"]
        assert "30" in entry_expr
        assert "70" in exit_expr

    def test_custom_params_reflected(self):
        s = rsi_threshold_long(period=20, entry_threshold=25.0, exit_threshold=75.0)
        ind = s.indicators[0]
        assert ind.params["period"] == 20
        assert "25" in s.condition_tree["long_entry"]["expr"]
        assert "75" in s.condition_tree["long_exit"]["expr"]

    def test_leaf_format(self):
        s = rsi_threshold_long()
        for slot in ("long_entry", "long_exit"):
            node = s.condition_tree[slot]
            assert node["op"] == "leaf"
            assert isinstance(node["expr"], str)

    def test_to_dict_roundtrip(self):
        s = rsi_threshold_long()
        d = s.to_dict()
        assert d["condition_tree"]["long_entry"]["op"] == "leaf"
        assert len(d["indicators"]) == 1

    def test_defaults_set(self):
        s = rsi_threshold_long()
        assert s.defaults.get("open_hour") == 9.5
        assert s.defaults.get("close_hour") == 16.0


# ---------------------------------------------------------------------------
# sma_crossover
# ---------------------------------------------------------------------------

class TestSmaCrossover:
    def test_returns_strategy(self):
        _assert_valid_strategy(sma_crossover())

    def test_long_only(self):
        _assert_long_only(sma_crossover())

    def test_four_indicators(self):
        s = sma_crossover()
        assert len(s.indicators) == 4

    def test_two_sma_indicators(self):
        s = sma_crossover()
        sma_inds = [i for i in s.indicators if i.name == "sma"]
        assert len(sma_inds) == 2

    def test_cross_transform_indicators(self):
        s = sma_crossover()
        names = {i.name for i in s.indicators}
        assert "cross_above" in names
        assert "cross_below" in names

    def test_cross_above_upstream_links_to_smas(self):
        s = sma_crossover()
        x_above = next(i for i in s.indicators if i.name == "cross_above")
        assert len(x_above.upstream) == 2

    def test_custom_periods(self):
        s = sma_crossover(fast=5, slow=20)
        sma_inds = [i for i in s.indicators if i.name == "sma"]
        periods = {i.params["period"] for i in sma_inds}
        assert periods == {5, 20}

    def test_leaf_format(self):
        s = sma_crossover()
        for slot in ("long_entry", "long_exit"):
            node = s.condition_tree[slot]
            assert node["op"] == "leaf"


# ---------------------------------------------------------------------------
# donchian_breakout
# ---------------------------------------------------------------------------

class TestDonchianBreakout:
    def test_returns_strategy(self):
        _assert_valid_strategy(donchian_breakout())

    def test_long_only(self):
        _assert_long_only(donchian_breakout())

    def test_five_indicators(self):
        s = donchian_breakout()
        assert len(s.indicators) == 5

    def test_uses_rolling_max_min(self):
        s = donchian_breakout()
        names = {i.name for i in s.indicators}
        assert "rolling_max" in names
        assert "rolling_min" in names

    def test_uses_high_low_close_primitives(self):
        s = donchian_breakout()
        names = {i.name for i in s.indicators}
        assert "high" in names
        assert "low" in names
        assert "close" in names

    def test_custom_period(self):
        s = donchian_breakout(period=55)
        roll_inds = [i for i in s.indicators if i.name in ("rolling_max", "rolling_min")]
        for i in roll_inds:
            assert i.params["period"] == 55

    def test_upstream_links_primitives_to_rolls(self):
        s = donchian_breakout()
        dc_upper = next(i for i in s.indicators if i.name == "rolling_max")
        dc_lower = next(i for i in s.indicators if i.name == "rolling_min")
        assert len(dc_upper.upstream) == 1
        assert len(dc_lower.upstream) == 1

    def test_leaf_format(self):
        s = donchian_breakout()
        for slot in ("long_entry", "long_exit"):
            node = s.condition_tree[slot]
            assert node["op"] == "leaf"


# ---------------------------------------------------------------------------
# buy_and_hold
# ---------------------------------------------------------------------------

class TestBuyAndHold:
    def test_returns_strategy(self):
        _assert_valid_strategy(buy_and_hold())

    def test_entry_not_none(self):
        s = buy_and_hold()
        assert s.condition_tree["long_entry"] is not None

    def test_long_exit_is_none(self):
        s = buy_and_hold()
        assert s.condition_tree["long_exit"] is None

    def test_no_shorts(self):
        s = buy_and_hold()
        assert s.condition_tree["short_entry"] is None
        assert s.condition_tree["short_exit"] is None

    def test_entry_condition_trivially_true(self):
        s = buy_and_hold()
        expr = s.condition_tree["long_entry"]["expr"]
        assert "> 0" in expr or "== 1" in expr or ">= 1" in expr

    def test_uses_close_primitive(self):
        s = buy_and_hold()
        names = {i.name for i in s.indicators if isinstance(i, Indicator)}
        assert "close" in names

    def test_to_dict_roundtrip(self):
        s = buy_and_hold()
        d = s.to_dict()
        assert d["condition_tree"]["long_exit"] is None
