"""Custom strategy — grouped-knob classes (Execution / Costs / Risk / Sizing).

Demonstrates: building a custom strategy with expression strings and
indicator references, then running it with explicit execution config.

Full indicator library (names, params, output columns):
    https://api.backtest360.com/docs#tag/Reference/operation/list_indicators_api_indicators_get

Requirements (beyond backtest360-client):
    pip install yfinance
"""

import os

import yfinance as yf

from backtest360 import Client, Costs, Execution, Risk, Sizing, Strategy

# ---------------------------------------------------------------------------
# Download data
# ---------------------------------------------------------------------------

df = yf.download(
    "SPY",
    start="2018-01-01",
    end="2024-01-01",
    interval="1d",
    auto_adjust=False,
    multi_level_index=False,
    progress=False,
)
df.columns = df.columns.str.lower()

spy_df = yf.download(
    "SPY",
    start="2018-01-01",
    end="2024-01-01",
    interval="1d",
    auto_adjust=False,
    multi_level_index=False,
    progress=False,
)
spy_df.columns = spy_df.columns.str.lower()

# ---------------------------------------------------------------------------
# Build strategy
# ---------------------------------------------------------------------------

# "rsi" is the ref — use it in expressions.  Strategy.indicator() defaults
# ref to the indicator name, so "rsi < 30" matches.
# For disambiguation (two RSIs at different periods), pass ref= explicitly:
#   Strategy.indicator("rsi", ref="rsi_fast", period=5)
#   Strategy.indicator("rsi", ref="rsi_slow", period=20)

strat = Strategy(
    name="rsi_mean_reversion",
    long_entry="rsi < 30",
    long_exit="rsi > 70",
    indicators=[Strategy.indicator("rsi", period=14)],
)

# ---------------------------------------------------------------------------
# Run backtest with all knobs
# ---------------------------------------------------------------------------

result = Client(api_key=os.environ["BACKTEST360_API_KEY"]).backtest(
    strat,
    df,
    benchmark=spy_df,
    execution=Execution(entry="open", exit="close", signal_frequency="daily"),
    costs=Costs(slippage_bps=2.5, fee_pct=0.001),
    risk=Risk(stop="trailing_atr", value=2.5, atr_period=14, max_drawdown=0.25),
    sizing=Sizing(weight=1.0, vol_target=0.15, leverage_limit=2.0),
)

# ---------------------------------------------------------------------------
# Inspect
# ---------------------------------------------------------------------------

print("Sharpe:", result.stats.get("Sharpe"))
print("Max Drawdown:", result.stats.get("Max Drawdown"))

for t in result.trades[:5]:
    print(t["entry_date"], t["direction"], t["return_net"])
