# backtest360-client

[![PyPI version](https://img.shields.io/pypi/v/backtest360-client.svg)](https://pypi.org/project/backtest360-client/)
[![CI](https://github.com/Backtest360/backtest360-client/actions/workflows/ci.yml/badge.svg)](https://github.com/Backtest360/backtest360-client/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/backtest360-client.svg)](https://pypi.org/project/backtest360-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

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

---

## Install

```bash
pip install --pre backtest360-client   # while on alpha
```

Requires Python 3.9+. The only runtime dependencies are `httpx` and `pandas`.

## Get an API key

Sign up at [backtest360.com/dashboard](https://backtest360.com/dashboard) and copy your key.
Store it in the `BACKTEST360_API_KEY` environment variable or pass it directly:

```python
client = Client(api_key="b360_live_...")
# or: export BACKTEST360_API_KEY=b360_live_...
client = Client()
```

---

## Features

- Hand-written wrapper over the public REST API — no generated code, no schema sync
- Built-in strategy templates (`Strategy.rsi_threshold_long()`, `Strategy.ma_crossover()`, …)
- Grouped-knob classes: `Execution`, `Costs`, `Risk`, `Sizing` — set only what you need
- Pandas-native — pass a DataFrame, get a DataFrame back (`result.equity`, `result.returns`)
- Raw-API escape hatch for full control (`client.backtest_raw({...})`)
- Strict type hints + `py.typed` — first-class IDE and mypy support
- MIT licensed

---

## Common patterns

### Custom strategy

```python
from backtest360 import Client, Strategy, Execution, Costs, Risk, Sizing

strat = Strategy(
    name="rsi_mean_reversion",
    long_entry="rsi < 30",
    long_exit="rsi > 70",
    indicators=[Strategy.indicator("rsi", period=14)],
)

result = Client(api_key="b360_live_...").backtest(
    strat, df,
    benchmark=spy_df,
    execution=Execution(entry="open", exit="close", signal_frequency="daily"),
    costs=Costs(slippage_bps=2.5, fee_pct=0.001),
    risk=Risk(stop="trailing_atr", value=2.5, atr_period=14, max_drawdown=0.25),
    sizing=Sizing(weight=1.0, vol_target=0.15, leverage_limit=2.0),
)

print(result.stats["Sharpe"], result.stats["Max Drawdown"])
for t in result.trades[:5]:
    print(t["entry_date"], t["direction"], t["return_net"])
```

> **Indicator library** (names, params, output columns):
> https://api.backtest360.com/docs#tag/Reference/operation/list_indicators_api_indicators_get
>
> **Strategy templates** (full list):
> https://api.backtest360.com/docs#tag/Reference/operation/list_strategies_api_strategies_get

### Raw API escape hatch

For users who want exact control with the API docs open:

```python
resp = Client(api_key="...").backtest_raw({
    "strategy":    {"condition_tree": {...}, "indicators": [...]},
    "data_source": {"ohlcv": {...}},
    "execution":   {"signal_frequency": "daily"},
})
```

### Error handling

```python
from backtest360 import Backtest360Error

try:
    result = client.backtest(strategy, df)
except Backtest360Error as e:
    if e.status == 401:
        print("Invalid or expired API key — renew at backtest360.com/dashboard")
    elif e.status == 429:
        print("Rate limited — retry after a moment")
    elif e.status == 422:
        print("Strategy validation failed:", e.body)
    else:
        raise   # unexpected — let it propagate
```

---

## Versioning

`MAJOR.MINOR.PATCH`. Pre-1.0 (`0.x.y`): the API may move between minor versions.
Pre-release suffixes: `aN` (alpha), `bN` (beta), `rcN` (release candidate).
See [CHANGELOG.md](CHANGELOG.md) for the release history.

---

## Full documentation

Full documentation → https://backtest360.github.io/backtest360-client/

Engine API reference → https://api.backtest360.com/docs

## Contributing / issues

Bug reports and feature requests welcome — open an issue on
[GitHub](https://github.com/Backtest360/backtest360-client/issues) or email
developers@backtest360.com.

## License

MIT — see [LICENSE](LICENSE).
