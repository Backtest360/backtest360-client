"""Quickstart — RSI threshold long-only strategy on BTC daily data.

Demonstrates: built-in template, minimal setup, equity plot.

Requirements (beyond backtest360-client):
    pip install yfinance matplotlib
"""

import os

import matplotlib.pyplot as plt
import yfinance as yf

from backtest360 import Client, Strategy

# ---------------------------------------------------------------------------
# Download data
# ---------------------------------------------------------------------------

df = yf.download(
    "BTC-USD",
    period="1y",
    interval="1d",
    auto_adjust=False,
    multi_level_index=False,
    progress=False,
)
df.columns = df.columns.str.lower()

# ---------------------------------------------------------------------------
# Run backtest
# ---------------------------------------------------------------------------

client = Client(api_key=os.environ["BACKTEST360_API_KEY"])
result = client.backtest(Strategy.rsi_threshold_long(), df)

# ---------------------------------------------------------------------------
# Inspect results
# ---------------------------------------------------------------------------

print("Sharpe:", result.stats.get("Sharpe"))
print("CAGR:", result.stats.get("CAGR"))
print("Max Drawdown:", result.stats.get("Max Drawdown"))
print(f"Trades: {len(result.trades)}")

result.equity.plot(title="BTC RSI threshold — equity curve")
plt.tight_layout()
plt.show()
