# Signal vs execution

The **signal frequency** (`Execution.signal_frequency`) is how often the
strategy evaluates its conditions — daily, hourly, 4h, etc.

The **entry/exit anchor** (`Execution.entry`, `Execution.exit`) is the bar
price used to fill the trade once a signal fires:

- `"open"` — fill at the next bar's open (one bar after the signal bar)
- `"close"` — fill at the signal bar's close

This separation means: a daily RSI signal fires at the close of bar D; with
`entry="open"` the position opens at the open of bar D+1. This is the
default — it avoids look-ahead bias.

Full execution reference: <https://api.backtest360.com/docs>
