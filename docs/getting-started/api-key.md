# API key

1. Sign up at [backtest360.com/dashboard](https://backtest360.com/dashboard).
2. Copy your API key (starts with `b360_live_` or `b360_test_`).
3. Store it in the `BACKTEST360_API_KEY` environment variable:

```bash
export BACKTEST360_API_KEY=b360_live_...
```

Or pass it directly:

```python
from backtest360 import Client
client = Client(api_key="b360_live_...")
```

If neither is set, `Client()` raises `Backtest360Error(status=401)` immediately.
