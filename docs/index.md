# backtest360-client

**Official Python client for the Backtest360 backtesting API.**

Backtest your trading strategy from every angle, in minutes.

```python
import yfinance as yf
from backtest360 import Client, Strategy

df = yf.download("BTC-USD", period="1y", interval="1d",
                 auto_adjust=False, multi_level_index=False, progress=False)
df.columns = df.columns.str.lower()

result = Client(api_key="b360_live_...").backtest(Strategy.rsi_threshold_long(), df)
print(result.stats["Sharpe"])
result.equity.plot(title="Equity curve")
```

## Install

```bash
pip install --pre backtest360-client   # while on alpha
```

## Where to go next

| Goal | Page |
|---|---|
| Get set up | [Getting started → Install](getting-started/install.md) |
| Understand the quickstart | [Getting started → First backtest](getting-started/first-backtest.md) |
| Build a custom strategy | [Tutorials → RSI mean reversion](tutorials/mean-reversion.md) |
| Set a stop-loss | [How-to → Set stops](how-to/set-stops.md) |
| Browse all classes | [API reference → Client](reference/client.md) |
| Understand the result object | [Concepts → Result anatomy](concepts/result-anatomy.md) |

## Links

- [Engine API reference](https://api.backtest360.com/docs)
- [GitHub](https://github.com/Backtest360/backtest360-client)
- [PyPI](https://pypi.org/project/backtest360-client/)
- [Changelog](https://github.com/Backtest360/backtest360-client/blob/main/CHANGELOG.md)
