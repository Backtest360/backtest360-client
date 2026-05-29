"""Tests for strategy.py — Execution, Costs, Risk, Sizing, MarketHours, Settings, Strategy."""

from __future__ import annotations

import pytest

from backtest360.strategy import Costs, Execution, MarketHours, Risk, Settings, Sizing, Strategy


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def test_execution_defaults():
    e = Execution()
    assert e.entry == "open"
    assert e.exit == "close"
    assert e.signal_frequency == "daily"
    assert e.entry_window == 0
    assert e.exit_window == 0
    assert e.entry_fill == "exact"
    assert e.exit_fill == "exact"


def test_execution_to_wire_defaults():
    w = Execution().to_wire()
    assert w["signal_frequency"] == "daily"
    assert w["entry_anchor"] == "open"
    assert w["exit_anchor"] == "close"
    assert w["entry_window"] == 0
    assert w["exit_window"] == 0
    assert w["entry_fill"] == "exact"
    assert w["exit_fill"] == "exact"


def test_execution_to_wire_custom():
    w = Execution(
        entry="close", exit="vwap", signal_frequency="hourly",
        entry_window=1, exit_window=2, entry_fill="worst", exit_fill="best",
    ).to_wire()
    assert w["entry_anchor"] == "close"
    assert w["exit_anchor"] == "vwap"
    assert w["signal_frequency"] == "hourly"
    assert w["entry_window"] == 1
    assert w["exit_window"] == 2
    assert w["entry_fill"] == "worst"
    assert w["exit_fill"] == "best"


def test_execution_entry_exit_fill_can_differ():
    w = Execution(entry_fill="worst", exit_fill="exact").to_wire()
    assert w["entry_fill"] == "worst"
    assert w["exit_fill"] == "exact"


# ---------------------------------------------------------------------------
# Costs
# ---------------------------------------------------------------------------


def test_costs_defaults():
    c = Costs()
    assert c.slippage_bps == 0.0
    assert c.fee_pct == 0.0
    assert c.vol_scaled_slippage is False
    assert c.vol_slippage_lookback == 20


def test_costs_to_wire():
    w = Costs(slippage_bps=5.0, fee_pct=0.001, vol_scaled_slippage=True, vol_slippage_lookback=30).to_wire()
    assert w["slippage_bps"] == 5.0
    assert w["fee_pct"] == 0.001
    assert w["vol_scaled_slippage"] is True
    assert w["vol_slippage_lookback"] == 30


def test_costs_to_wire_defaults():
    w = Costs().to_wire()
    assert w["slippage_bps"] == 0.0
    assert w["fee_pct"] == 0.0
    assert w["vol_scaled_slippage"] is False
    assert w["vol_slippage_lookback"] == 20


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------


def test_risk_defaults():
    r = Risk()
    assert r.stop is None
    assert r.value is None
    assert r.atr_period is None
    assert r.reentry == "immediate"
    assert r.cooldown_bars == 0
    assert r.max_drawdown is None


def test_risk_to_wire_no_stop():
    w = Risk().to_wire()
    assert "stop_type" not in w
    assert "stop_value" not in w
    assert "stop_atr_period" not in w
    assert "max_drawdown_limit" not in w
    assert w["stop_reentry"] == "immediate"
    assert w["stop_cooldown_bars"] == 0


def test_risk_to_wire_trailing_atr():
    w = Risk(stop="trailing_atr", value=2.5, atr_period=14, reentry="next_signal", cooldown_bars=3).to_wire()
    assert w["stop_type"] == "trailing_atr"
    assert w["stop_value"] == 2.5
    assert w["stop_atr_period"] == 14
    assert w["stop_reentry"] == "next_signal"
    assert w["stop_cooldown_bars"] == 3


def test_risk_to_wire_fixed():
    w = Risk(stop="fixed", value=0.05).to_wire()
    assert w["stop_type"] == "fixed"
    assert w["stop_value"] == 0.05
    assert "stop_atr_period" not in w


def test_risk_to_wire_trailing():
    w = Risk(stop="trailing", value=0.10).to_wire()
    assert w["stop_type"] == "trailing"


def test_risk_to_wire_atr():
    w = Risk(stop="atr", value=2.0, atr_period=14).to_wire()
    assert w["stop_type"] == "atr"
    assert w["stop_atr_period"] == 14


def test_risk_to_wire_cooldown_reentry():
    w = Risk(stop="fixed", value=0.05, reentry="cooldown", cooldown_bars=5).to_wire()
    assert w["stop_reentry"] == "cooldown"
    assert w["stop_cooldown_bars"] == 5


def test_risk_to_wire_max_drawdown():
    w = Risk(max_drawdown=0.25).to_wire()
    assert w["max_drawdown_limit"] == 0.25


def test_risk_reentry_is_string():
    r = Risk()
    assert isinstance(r.reentry, str)


# ---------------------------------------------------------------------------
# Sizing
# ---------------------------------------------------------------------------


def test_sizing_defaults():
    s = Sizing()
    assert s.weight == 1.0
    assert s.vol_target is None
    assert s.vol_target_lookback == 20
    assert s.leverage_limit is None


def test_sizing_to_wire_defaults():
    w = Sizing().to_wire()
    assert w["position_weight"] == 1.0
    assert w["vol_target_lookback"] == 20
    assert "vol_target" not in w
    assert "leverage_limit" not in w


def test_sizing_to_wire_with_vol_target():
    w = Sizing(weight=0.5, vol_target=0.15, vol_target_lookback=30, leverage_limit=2.0).to_wire()
    assert w["position_weight"] == 0.5
    assert w["vol_target"] == 0.15
    assert w["vol_target_lookback"] == 30
    assert w["leverage_limit"] == 2.0


def test_sizing_leverage_limit_none_omitted():
    w = Sizing(leverage_limit=None).to_wire()
    assert "leverage_limit" not in w


def test_sizing_leverage_limit_set_emitted():
    w = Sizing(leverage_limit=1.5).to_wire()
    assert w["leverage_limit"] == 1.5


# ---------------------------------------------------------------------------
# MarketHours
# ---------------------------------------------------------------------------


def test_market_hours_defaults():
    m = MarketHours()
    assert m.open_hour is None
    assert m.close_hour is None
    assert m.strict_anchors is False


def test_market_hours_to_wire_defaults():
    w = MarketHours().to_wire()
    assert w["strict_anchors"] is False
    assert "open_hour" not in w
    assert "close_hour" not in w


def test_market_hours_to_wire_with_hours():
    w = MarketHours(open_hour=9.5, close_hour=16.0).to_wire()
    assert w["open_hour"] == 9.5
    assert w["close_hour"] == 16.0
    assert w["strict_anchors"] is False


def test_market_hours_to_wire_strict():
    w = MarketHours(open_hour=9.5, close_hour=16.0, strict_anchors=True).to_wire()
    assert w["strict_anchors"] is True


def test_market_hours_open_hour_only_omitted():
    w = MarketHours(close_hour=16.0).to_wire()
    assert "open_hour" not in w
    assert w["close_hour"] == 16.0


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_settings_defaults():
    s = Settings()
    assert s.risk_free_rate == 0.0
    assert s.random_seed == 42
    assert s.on_bad_data == "raise"


def test_settings_to_wire_defaults():
    w = Settings().to_wire()
    assert w["risk_free_rate"] == 0.0
    assert w["random_seed"] == 42
    assert w["on_bad_data"] == "raise"


def test_settings_to_wire_custom():
    w = Settings(risk_free_rate=0.04, random_seed=99, on_bad_data="zero").to_wire()
    assert w["risk_free_rate"] == 0.04
    assert w["random_seed"] == 99
    assert w["on_bad_data"] == "zero"


def test_settings_rfr_only():
    w = Settings(risk_free_rate=0.05).to_wire()
    assert w["risk_free_rate"] == 0.05
    assert w["on_bad_data"] == "raise"


# ---------------------------------------------------------------------------
# Strategy — constructor + to_wire
# ---------------------------------------------------------------------------


def test_strategy_minimal():
    s = Strategy(name="test")
    assert s.name == "test"
    assert s.long_entry is None
    assert s.long_exit is None
    assert s.short_entry is None
    assert s.short_exit is None
    assert s.indicators == []


def test_strategy_to_wire_long_only():
    s = Strategy(
        name="rsi",
        long_entry="rsi < 30",
        long_exit="rsi > 70",
        indicators=[Strategy.indicator("rsi", period=14)],
    )
    w = s.to_wire()
    assert w["condition_tree"]["long_entry"] == {"op": "leaf", "expr": "rsi < 30"}
    assert w["condition_tree"]["long_exit"]  == {"op": "leaf", "expr": "rsi > 70"}
    assert w["condition_tree"]["short_entry"] is None
    assert w["condition_tree"]["short_exit"]  is None
    assert len(w["indicators"]) == 1
    assert w["indicators"][0]["name"] == "rsi"


def test_strategy_to_wire_short_slots():
    s = Strategy(
        name="long_short",
        long_entry="rsi < 30",
        long_exit="rsi > 70",
        short_entry="rsi > 70",
        short_exit="rsi < 30",
    )
    w = s.to_wire()
    assert w["condition_tree"]["short_entry"] == {"op": "leaf", "expr": "rsi > 70"}
    assert w["condition_tree"]["short_exit"]  == {"op": "leaf", "expr": "rsi < 30"}


def test_strategy_to_wire_no_entries_gives_null_nodes():
    w = Strategy(name="empty").to_wire()
    ct = w["condition_tree"]
    assert ct["long_entry"] is None
    assert ct["long_exit"] is None
    assert ct["short_entry"] is None
    assert ct["short_exit"] is None


# ---------------------------------------------------------------------------
# Strategy.indicator()
# ---------------------------------------------------------------------------


def test_indicator_defaults():
    ind = Strategy.indicator("rsi", period=14)
    assert ind["name"] == "rsi"
    assert ind["ref"] == "rsi"
    assert ind["kind"] == "technical"
    assert ind["params"] == {"period": 14}
    assert ind["upstream"] == []


def test_indicator_custom_ref():
    ind = Strategy.indicator("rsi", ref="rsi_fast", period=5)
    assert ind["ref"] == "rsi_fast"
    assert ind["name"] == "rsi"
    assert ind["params"] == {"period": 5}


def test_indicator_transform():
    ind = Strategy.indicator(
        "cross_above", ref="x_above", kind="transform", upstream=["sma_10", "sma_50"]
    )
    assert ind["name"] == "cross_above"
    assert ind["ref"] == "x_above"
    assert ind["kind"] == "transform"
    assert ind["upstream"] == ["sma_10", "sma_50"]
    assert ind["params"] == {}


def test_indicator_no_params():
    ind = Strategy.indicator("rsi_regime")
    assert ind["params"] == {}
    assert ind["upstream"] == []


def test_indicator_multiple_params():
    ind = Strategy.indicator("bbands", period=20, nbdev=2.0)
    assert ind["params"]["period"] == 20
    assert ind["params"]["nbdev"] == 2.0


# ---------------------------------------------------------------------------
# Strategy templates
# ---------------------------------------------------------------------------


def test_rsi_threshold_long_shape():
    s = Strategy.rsi_threshold_long()
    w = s.to_wire()
    assert w["condition_tree"]["long_entry"]["expr"] == "rsi_14 < 30"
    assert w["condition_tree"]["long_exit"]["expr"] == "rsi_14 > 70"
    assert w["condition_tree"]["short_entry"] is None
    assert len(w["indicators"]) == 1
    assert w["indicators"][0]["name"] == "rsi"
    assert w["indicators"][0]["ref"] == "rsi_14"
    assert w["indicators"][0]["params"]["period"] == 14


def test_rsi_mean_reversion_shape():
    s = Strategy.rsi_mean_reversion()
    w = s.to_wire()
    assert w["condition_tree"]["long_entry"]["expr"] == "rsi_14 < 30"
    assert len(w["indicators"]) == 1


def test_ma_crossover_shape():
    s = Strategy.ma_crossover()
    w = s.to_wire()
    assert w["condition_tree"]["long_entry"]["expr"] == "x_above"
    assert w["condition_tree"]["long_exit"]["expr"] == "x_below"
    refs = {i["ref"] for i in w["indicators"]}
    assert refs == {"sma_10", "sma_50", "x_above", "x_below"}
    x_above = next(i for i in w["indicators"] if i["ref"] == "x_above")
    assert "sma_10" in x_above["upstream"]
    assert "sma_50" in x_above["upstream"]
    assert x_above["kind"] == "transform"


def test_momentum_6m_long_shape():
    s = Strategy.momentum_6m_long()
    w = s.to_wire()
    assert w["condition_tree"]["long_entry"]["expr"] == "roc_126 > 0"
    assert len(w["indicators"]) == 1
    assert w["indicators"][0]["name"] == "roc"
    assert w["indicators"][0]["params"]["period"] == 126


def test_templates_return_new_instances():
    s1 = Strategy.rsi_threshold_long()
    s2 = Strategy.rsi_threshold_long()
    assert s1 is not s2


# ---------------------------------------------------------------------------
# Import from package
# ---------------------------------------------------------------------------


def test_all_importable_from_package():
    from backtest360 import Costs as C  # noqa: F401
    from backtest360 import Execution as E  # noqa: F401
    from backtest360 import MarketHours as MH  # noqa: F401
    from backtest360 import Risk as R  # noqa: F401
    from backtest360 import Settings as Se  # noqa: F401
    from backtest360 import Sizing as S  # noqa: F401
    from backtest360 import Strategy as St  # noqa: F401

    assert E is Execution
    assert C is Costs
    assert R is Risk
    assert S is Sizing
    assert MH is MarketHours
    assert Se is Settings
    assert St is Strategy
