"""Error handling — catching Backtest360Error and branching on .status.

Demonstrates all common error cases and how to handle them.
"""

import os

import pandas as pd

from backtest360 import Backtest360Error, Client, Strategy


def run_with_error_handling():
    client = Client(api_key=os.environ.get("BACKTEST360_API_KEY", "invalid_key"))

    # Minimal DataFrame — will likely fail validation but shows the flow
    df = pd.DataFrame({
        "open":  [100.0, 101.0],
        "high":  [102.0, 103.0],
        "low":   [99.0,  100.0],
        "close": [101.0, 102.0],
    }, index=pd.date_range("2020-01-01", periods=2, freq="D"))

    try:
        result = client.backtest(Strategy.rsi_threshold_long(), df)
        print("Success! Sharpe:", result.stats.get("Sharpe"))

    except Backtest360Error as e:
        if e.status == 401:
            print("Invalid or expired API key.")
            print("Renew at: https://backtest360.com/dashboard")

        elif e.status == 403:
            print("Your key lacks the required scope for this endpoint.")

        elif e.status == 422:
            print("Strategy or config is invalid.")
            if isinstance(e.body, dict):
                print("Details:", e.body.get("detail"))

        elif e.status == 429:
            print("Rate limited or quota exceeded. Retry later.")

        elif e.status and e.status >= 500:
            print(f"Engine error ({e.status}). Request ID: {e.request_id}")
            raise  # unexpected — let it propagate

        else:
            raise  # unknown status — re-raise


if __name__ == "__main__":
    run_with_error_handling()
