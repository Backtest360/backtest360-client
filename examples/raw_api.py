"""Raw API escape hatch — backtest_raw() for full wire-level control.

Use when you want to build the exact JSON payload yourself with the API
docs open, bypassing the SDK's helper classes entirely.

API reference: https://api.backtest360.com/docs#tag/Backtest/operation/backtest_api_backtest_post

Requirements (beyond backtest360-client):
    pip install yfinance
"""

import os

import yfinance as yf

from backtest360 import Client

# ---------------------------------------------------------------------------
# Download and serialise data manually
# ---------------------------------------------------------------------------

df = yf.download(
    "BTC-USD", period="1y", interval="1d",
    auto_adjust=False, multi_level_index=False, progress=False,
)
df.columns = df.columns.str.lower()

ohlcv = {
    "dates": [str(ts) for ts in df.index],
    "open":  df["open"].tolist(),
    "high":  df["high"].tolist(),
    "low":   df["low"].tolist(),
    "close": df["close"].tolist(),
    "volume": df["volume"].tolist(),
}

# ---------------------------------------------------------------------------
# Build the raw payload — matches /api/backtest exactly
# ---------------------------------------------------------------------------

payload = {
    "strategy": {
        "condition_tree": {
            "long_entry":  {"op": "leaf", "expr": "rsi_14 < 30"},
            "long_exit":   {"op": "leaf", "expr": "rsi_14 > 70"},
            "short_entry": None,
            "short_exit":  None,
        },
        "indicators": [
            {
                "ref":      "rsi_14",
                "name":     "rsi",
                "kind":     "technical",
                "params":   {"period": 14},
                "upstream": [],
            },
        ],
    },
    "data_source": {
        "ohlcv": ohlcv,
    },
    "execution": {
        "signal_frequency": "daily",
        "entry_anchor":     "open",
        "exit_anchor":      "close",
        "slippage_bps":     2.5,
        "fee_pct":          0.001,
    },
}

# ---------------------------------------------------------------------------
# Send and inspect the raw response
# ---------------------------------------------------------------------------

client = Client(api_key=os.environ["BACKTEST360_API_KEY"])
resp = client.backtest_raw(payload)

# resp is the full engine response dict — "result" key + everything inside
result = resp.get("result", resp)
print("Sharpe:", result.get("stats", {}).get("Sharpe"))
print("Keys in result:", list(result.keys()))
