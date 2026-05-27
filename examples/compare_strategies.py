"""Compare two strategies side-by-side on the same data.

Runs two backtests and plots both equity curves for visual comparison.

Requirements (beyond backtest360-client):
    pip install yfinance matplotlib
"""

import os

import matplotlib.pyplot as plt
import yfinance as yf

from backtest360 import Client, Strategy

# ---------------------------------------------------------------------------

df = yf.download(
    "SPY", start="2018-01-01", end="2024-01-01", interval="1d",
    auto_adjust=False, multi_level_index=False, progress=False,
)
df.columns = df.columns.str.lower()

client = Client(api_key=os.environ["BACKTEST360_API_KEY"])

result_rsi = client.backtest(Strategy.rsi_mean_reversion(), df)
result_mom = client.backtest(Strategy.momentum_6m_long(), df)

# ---------------------------------------------------------------------------

fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

result_rsi.equity.plot(ax=axes[0], title="RSI Mean Reversion", color="steelblue")
result_mom.equity.plot(ax=axes[1], title="6-Month Momentum", color="darkorange")

for ax in axes:
    ax.set_ylabel("Equity")
    ax.grid(alpha=0.3)

print("RSI Sharpe:", result_rsi.stats.get("Sharpe"),
      "  Momentum Sharpe:", result_mom.stats.get("Sharpe"))

plt.tight_layout()
plt.show()
