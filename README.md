# backtest360-client

This client accesses the Backtest360 Public API.

Backtest your trading strategy from every angle, in minutes.

---

## Getting started (step by step)

### Step 1 — Get Python

You need Python 3.10 or newer.

**Windows (easiest):** Download the installer from [python.org](https://www.python.org/downloads/) and run it. Tick "Add Python to PATH" during setup.

**Windows Subsystem for Linux (WSL):** Open a WSL terminal (search "Ubuntu" or "WSL" in the Start menu) and run:

```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv -y
python3 --version   # should print 3.10 or newer
```

**Mac:** Install [Homebrew](https://brew.sh), then:

```bash
brew install python@3.12
python3 --version
```

---

### Step 2 — Create a virtual environment (recommended)

A virtual environment keeps your project packages separate from the system Python.

**Windows (Command Prompt or PowerShell):**

```
python -m venv .venv
.venv\Scripts\activate
```

**Mac / Linux / WSL:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt will show `(.venv)` when it's active. Run `deactivate` to exit it.

---

### Step 3 — Install the SDK

```bash
pip install backtest360-client
```

That's it. No extra dependencies to manage — pandas and httpx come along automatically.

---

### Step 4 — Get an API key

Sign up at [backtest360.com](https://backtest360.com) and grab your API key from the dashboard. It starts with `b360_live_`.

Set it as an environment variable so you never hardcode it in scripts:

**Windows (PowerShell):**

```powershell
$env:BACKTEST360_API_KEY = "b360_live_your_key_here"
```

**Mac / Linux / WSL:**

```bash
export BACKTEST360_API_KEY="b360_live_your_key_here"
```

To make it permanent, add that `export` line to `~/.bashrc` or `~/.zshrc`.

---

### Step 5 — Prepare your data

The SDK works with any OHLCV CSV file. Your file needs at least these columns:

```
date,open,high,low,close,volume
2020-01-02,296.24,300.60,295.19,300.35,33870100
2020-01-03,297.15,300.58,296.50,297.43,36580700
...
```

The date column should be the index (or the first column). Column names are case-insensitive.

---

### Step 6 — Run your first backtest

Save this as `my_backtest.py` and run it with `python my_backtest.py` (or `python3 my_backtest.py` on Mac/Linux):

```python
import os
import pandas as pd
from backtest360 import BacktestClient, BacktestConfig, MarketData
from backtest360.strategies import rsi_threshold_long

# --- Load your CSV ---
df = pd.read_csv("aapl.csv", index_col=0, parse_dates=True)
df.columns = df.columns.str.lower()   # normalise to lowercase

# --- Wrap in MarketData (auto-detects frequency, hours, data quality) ---
md = MarketData()
md.load(df)

# --- Pick a strategy ---
# Enter long when RSI(14) drops below 30; exit when it rises above 70
strategy = rsi_threshold_long(period=14, entry_threshold=30, exit_threshold=70)

# --- Configure execution ---
config = BacktestConfig(signal_frequency="daily")

# --- Run ---
client = BacktestClient()   # reads BACKTEST360_API_KEY from environment
result = client.backtest(strategy, config, md)

# --- Print results ---
s = result.statistics
print(f"CAGR:         {s.cagr:.2%}")
print(f"Sharpe ratio: {s.sharpe_ratio:.2f}")
print(f"Max drawdown: {s.max_drawdown:.2%}")
print(f"Win rate:     {s.win_rate:.2%}")
print(f"Total trades: {s.total_trades}")
```

Expected output (numbers vary by dataset):

```
CAGR:         14.32%
Sharpe ratio: 0.87
Max drawdown: -18.45%
Win rate:     52.10%
Total trades: 47
```

---

## What's next?

### Compare against a benchmark

```python
bm = MarketData()
bm.load(pd.read_csv("spy.csv", index_col=0, parse_dates=True))

result = client.backtest(strategy, config, md, benchmark=bm)
print(f"Alpha: {result.statistics.alpha:.4f}")
print(f"Beta:  {result.statistics.beta:.2f}")
```

### Try a different strategy

Four starter templates ship with the SDK:

```python
from backtest360.strategies import rsi_threshold_long, sma_crossover, donchian_breakout, buy_and_hold

s1 = rsi_threshold_long(period=14, entry_threshold=30, exit_threshold=70)
s2 = sma_crossover(fast=10, slow=50)
s3 = donchian_breakout(period=20)
s4 = buy_and_hold()   # always-long baseline
```

### Add costs and risk controls

```python
from backtest360.dtos import ExecutionCosts, RiskControls

config = BacktestConfig(
    signal_frequency="daily",
    costs=ExecutionCosts(slippage_bps=5, fee_pct=0.001),
    risk=RiskControls(stop_type="atr", stop_value=2.0),
)
```

### Check today's signal

```python
sig = client.latest_signal(strategy, config, md)
print(sig.signal)           # 1 = long, 0 = flat, -1 = short
print(sig.bar_timestamp)    # when the signal fired
```

---

## Build your own strategy

Use `Indicator` and `Strategy` to compose strategies from any of the engine's registered indicators:

```python
from backtest360.dtos import Indicator, Strategy

strategy = Strategy(
    name="my_strategy",
    indicators=[
        Indicator(id="rsi",  name="rsi",  params={"period": 14}, upstream=[]),
        Indicator(id="sma",  name="sma",  params={"period": 200}, upstream=[]),
    ],
    condition_tree={
        "long_entry":  {"op": "and", "args": [
            {"op": "leaf", "expr": "rsi < 40"},
            {"op": "leaf", "expr": "close > sma"},
        ]},
        "long_exit":   {"op": "leaf", "expr": "rsi > 60"},
        "short_entry": None,
        "short_exit":  None,
    },
)
```

Call `client.list_indicators()` to see all available indicator ids and their parameter schemas.

---

## Error handling

```python
from backtest360.exceptions import (
    AuthenticationError, EngineError, QuotaExceededError, RateLimitError, ValidationError,
)

try:
    result = client.backtest(strategy, config, md)
except AuthenticationError:
    print("Bad or missing API key. Check BACKTEST360_API_KEY.")
except QuotaExceededError as e:
    print(f"Daily quota exhausted ({e.used}/{e.limit}). Upgrade your plan.")
except RateLimitError as e:
    print(f"Too many requests. Retry in {e.retry_after}s.")
except ValidationError as e:
    print("Strategy validation failed:", e.issues)
except EngineError as e:
    print(f"Engine error {e.status}: {e}")
```

---

## Requirements

- Python 3.10+
- pandas >= 2.0
- httpx >= 0.27

---

## Links

- [backtest360.com](https://backtest360.com) — sign up, manage API keys, run strategies via the GUI
- [API reference](https://backtest360.com/docs/api) — full endpoint documentation
