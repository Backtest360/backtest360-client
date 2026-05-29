"""Benchmark comparison — alpha, beta, up/down capture.

Pass benchmark=spy_df to get benchmark-relative metrics in result.stats.
Metrics added when a benchmark is present: Alpha, Beta, Information Ratio,
Tracking Error, Up Capture, Down Capture.

Requirements (beyond backtest360-client):
    pip install yfinance
"""

import os

import yfinance as yf

from backtest360 import Client, Strategy

# ---------------------------------------------------------------------------

def _download(ticker):
    df = yf.download(
        ticker, start="2020-01-01", end="2024-01-01", interval="1d",
        auto_adjust=False, multi_level_index=False, progress=False,
    )
    df.columns = df.columns.str.lower()
    return df


df = _download("SPY")
benchmark = _download("SPY")  # same ticker for demo; use a different one in practice

client = Client(api_key=os.environ["BACKTEST360_API_KEY"])
result = client.backtest(Strategy.rsi_mean_reversion(), df, benchmark=benchmark)

print("Sharpe:", result.stats.get("Sharpe"))
print("Alpha:", result.stats.get("Alpha"))
print("Beta:", result.stats.get("Beta"))
print("Up Capture:", result.stats.get("Up Capture"))
print("Down Capture:", result.stats.get("Down Capture"))

import matplotlib.pyplot as plt
ax = result.strategy_equity.plot(label="Strategy")
result.benchmark_equity.plot(ax=ax, label="SPY (buy & hold)", linestyle="--")
ax.legend()
plt.tight_layout()
plt.show()
