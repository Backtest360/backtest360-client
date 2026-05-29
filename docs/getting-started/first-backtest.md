# First backtest

This walks through the 5-line quickstart step by step.

```python
import yfinance as yf
from backtest360 import Client, Strategy

df = yf.download("BTC-USD", period="1y", interval="1d",
                 auto_adjust=False, multi_level_index=False, progress=False)
df.columns = df.columns.str.lower()

result = Client(api_key="b360_live_...").backtest(Strategy.rsi_threshold_long(), df)
print(result.stats["Sharpe"])
result.strategy_equity.plot(title="Equity curve")
```

**Line by line:**

1. Download daily BTC data from Yahoo Finance.
2. Lowercase column names — the engine expects `open/high/low/close/volume`.
3. `Strategy.rsi_threshold_long()` — built-in RSI(14) < 30 / > 70 template.
4. `Client.backtest(strategy, df)` — sends the data and strategy to the engine.
5. `result.stats["Sharpe"]` — one of 120+ metrics in the response.
6. `result.strategy_equity.plot()` — equity curve as a `pd.Series` indexed by datetime.

See [Result anatomy](../concepts/result-anatomy.md) for the full result shape.
