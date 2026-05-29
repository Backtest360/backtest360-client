# Result anatomy

`client.backtest(...)` returns a `Result` object. All properties are read-only
and derived lazily from the raw engine response.

## `result.stats`

A `dict` of 120+ performance metrics. Common keys:

| Key | Description |
|---|---|
| `"Sharpe"` | Annualised Sharpe ratio |
| `"Sortino"` | Annualised Sortino ratio |
| `"CAGR"` | Compound annual growth rate |
| `"Max Drawdown"` | Maximum peak-to-trough drawdown (negative) |
| `"Vol (Ann)"` | Annualised volatility |
| `"Total Trades"` | Number of completed round-trips |
| `"Alpha"` | Jensen's alpha (only when benchmark provided) |
| `"Beta"` | Market beta (only when benchmark provided) |

Use `result.raw["stats"]` (or `result.stats`) for the complete dict.

## `result.trades`

A `list` of trade dicts. Each dict has:

- `entry_date`, `exit_date` — ISO timestamp strings
- `direction` — `1` (long) or `-1` (short)
- `entry_price`, `exit_price`
- `return_net` — net-of-cost log return for this trade
- `return_gross` — gross log return
- `holding_bars` — number of bars held
- `exit_reason` — `"exit_signal"`, `"stop_loss"`, `"max_drawdown"`, etc.
- `cumulative_pnl` — running sum of `return_net` across all trades to this point

## `result.strategy_equity` / `result.benchmark_equity` / `result.returns` / `result.signals`

All are `pd.Series` indexed by `datetime64`:

```python
ax = result.strategy_equity.plot(title="Equity curve")   # starts at 1.0
result.benchmark_equity.plot(ax=ax, linestyle="--")       # present when benchmark was supplied
result.returns.cumsum().plot(title="Cumulative")          # log-returns
result.signals.value_counts()                             # {-1, 0, 1} distribution
```

`benchmark_equity` is an empty Series when no `benchmark` was passed to `backtest()` — safe to plot unconditionally.

## `result.raw`

The full `dict` from the engine — everything not exposed as a property:

```python
result.raw["monthly_returns"]    # list of {period, return} dicts
result.raw["rolling_statistics"] # rolling 12-month Sharpe, vol, return
result.raw["signal_diagnostics"] # per-bar condition firings
result.raw["results_df"]         # full per-bar state table
```
