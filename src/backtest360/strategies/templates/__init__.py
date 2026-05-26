"""Starter strategy template factories."""

from backtest360.strategies.templates.buy_and_hold import buy_and_hold
from backtest360.strategies.templates.donchian_breakout import donchian_breakout
from backtest360.strategies.templates.rsi_threshold_long import rsi_threshold_long
from backtest360.strategies.templates.sma_crossover import sma_crossover

__all__ = ["rsi_threshold_long", "sma_crossover", "donchian_breakout", "buy_and_hold"]
