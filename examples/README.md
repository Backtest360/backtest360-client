# Examples

Runnable scripts demonstrating the Backtest360 Python client.

Each script is self-contained. Install requirements:

```bash
pip install --pre backtest360-client yfinance matplotlib
```

Set your API key:

```bash
export BACKTEST360_API_KEY=b360_live_...
```

| Script | What it demonstrates |
|---|---|
| `quickstart_yahoo_btc.py` | 5-line quickstart — built-in template, BTC daily data |
| `custom_strategy.py` | Custom RSI strategy with Execution / Costs / Risk / Sizing |
| `raw_api.py` | `backtest_raw()` escape hatch — full control over the wire payload |
| `with_benchmark.py` | Pass a benchmark DataFrame, read alpha / beta / capture |
| `error_handling.py` | Catch `Backtest360Error`, branch on `.status` |
| `compare_strategies.py` | Run two strategies on the same data, plot both equity curves |
