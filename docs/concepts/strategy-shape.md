# Strategy shape

A `Strategy` has two parts:

1. **`condition_tree`** — four boolean slots (`long_entry`, `long_exit`,
   `short_entry`, `short_exit`). Each slot is either `None` or a boolean
   expression string. The SDK converts bare strings to leaf nodes:
   `"rsi < 30"` → `{"op": "leaf", "expr": "rsi < 30"}`.

2. **`indicators`** — a flat list of indicator descriptor dicts produced by
   `Strategy.indicator(...)`. Each descriptor declares a `ref` (the column
   name used in expressions), a `name` (indicator type), `kind`, `params`,
   and `upstream` (for transform indicators that chain off other indicators).

## Expression strings

Expression strings are evaluated by the engine as `pandas.DataFrame.eval`
comparisons. The column names in expressions are the `ref` values from the
`indicators` list.

```python
# "rsi" is the ref — declared in the indicator list, referenced in expressions
Strategy(
    name="my_strat",
    long_entry="rsi < 30",
    long_exit="rsi > 70",
    indicators=[Strategy.indicator("rsi", period=14)],
)
```

Multi-condition expressions use `&` and `|`:
```python
long_entry="(rsi < 30) & (volume > 1000000)"
```

## Indicator refs

The `ref` is the column name in the expression. By default `Strategy.indicator(name, **params)`
sets `ref=name`. Use an explicit `ref=` when the same indicator appears with
different params:

```python
indicators=[
    Strategy.indicator("rsi", ref="rsi_fast", period=5),
    Strategy.indicator("rsi", ref="rsi_slow", period=20),
]
# Then in expressions: "rsi_fast < rsi_slow"
```

## Transform indicators

Transform indicators (e.g. `cross_above`, `cross_below`, `zscore`, `lag`,
`diff`) consume another indicator's output column. Declare them with
`kind="transform"` and an `upstream=` list:

```python
Strategy(
    name="sma_crossover",
    long_entry="x_above",
    long_exit="x_below",
    indicators=[
        Strategy.indicator("sma", ref="sma_10", period=10),
        Strategy.indicator("sma", ref="sma_50", period=50),
        Strategy.indicator("cross_above", ref="x_above", kind="transform",
                           upstream=["sma_10", "sma_50"]),
        Strategy.indicator("cross_below", ref="x_below", kind="transform",
                           upstream=["sma_10", "sma_50"]),
    ],
)
```

Full indicator library: <https://api.backtest360.com/docs#tag/Reference/operation/list_indicators_api_indicators_get>
