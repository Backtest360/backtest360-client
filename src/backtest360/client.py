"""BacktestClient — HTTP orchestrator for the Backtest360 engine.

Sync httpx transport only (v0.1). Resolves API key from:
  1. Explicit api_key= argument
  2. BACKTEST360_API_KEY environment variable
  3. Raises AuthenticationError immediately on first request

Every request sends X-Client-Version for server-side adoption telemetry.
"""

from __future__ import annotations

import json
import os
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

import httpx

from backtest360.dtos import (
    BacktestConfig,
    BacktestResult,
    LatestSignalResult,
    MarketData,
    Strategy,
    ValidationResult,
)
from backtest360.exceptions import (
    AuthenticationError,
    EngineError,
    QuotaExceededError,
    RateLimitError,
    ValidationError,
)

_DEFAULT_BASE_URL = "https://api.backtest360.com"
_TIMEOUT_SECONDS = 300  # backtests can be slow


def _sdk_version() -> str:
    try:
        return version("backtest360-client")
    except PackageNotFoundError:
        return "0.0.0.dev"


def _resolve_api_key(api_key: Optional[str]) -> str:
    if api_key:
        return api_key
    env_key = os.environ.get("BACKTEST360_API_KEY", "")
    if env_key:
        return env_key
    raise AuthenticationError(
        "No API key. Set the BACKTEST360_API_KEY environment variable "
        "or pass api_key=... to BacktestClient. Sign up at backtest360.com."
    )


def _handle_error(response: httpx.Response) -> None:
    """Map HTTP error responses to SDK exceptions."""
    if response.status_code < 400:
        return

    try:
        body = response.json()
    except Exception:
        body = {}

    detail = body.get("detail", {})
    if isinstance(detail, str):
        message = detail
        code = ""
    elif isinstance(detail, list):
        message = ""
        code = ""
    else:
        message = detail.get("message", response.text)
        code = detail.get("code", "")

    request_id = response.headers.get("x-request-id")
    retry_after_raw = response.headers.get("Retry-After")
    retry_after = int(retry_after_raw) if retry_after_raw and retry_after_raw.isdigit() else None

    status = response.status_code

    if status == 401:
        raise AuthenticationError(message or "Invalid or revoked API key. Generate a new one at backtest360.com/dashboard.")

    if status == 403:
        raise AuthenticationError(message or "Your key lacks the required scope for this endpoint.")

    if status == 422:
        issues = [i.get("msg", str(i)) for i in body.get("detail", [])] if isinstance(body.get("detail"), list) else []
        raise ValidationError(message or "Strategy or config is invalid.", issues=issues)

    if status == 426:
        raise EngineError(
            message or "Client is too old. Upgrade with: pip install -U backtest360-client",
            status=status,
            request_id=request_id,
        )

    if status == 429:
        if "quota" in message.lower() or code == "QUOTA_EXCEEDED":
            used = body.get("used")
            limit = body.get("limit")
            raise QuotaExceededError(message, used=used, limit=limit)
        raise RateLimitError(message, retry_after=retry_after)

    raise EngineError(
        message or f"Backtest360 service error. Status: {status}.",
        status=status,
        request_id=request_id,
    )


class BacktestClient:
    """Synchronous HTTP client for the Backtest360 engine.

    Usage::

        from backtest360 import BacktestClient, BacktestConfig, MarketData
        from backtest360.strategies import rsi_threshold_long

        md = MarketData()
        md.load(df)

        bt = BacktestClient(api_key="b360_live_...")
        result = bt.backtest(rsi_threshold_long(), BacktestConfig(), md)
        print(result.statistics.sharpe_ratio)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _TIMEOUT_SECONDS,
    ) -> None:
        self._api_key = _resolve_api_key(api_key)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._sdk_version = _sdk_version()

    def _headers(self) -> dict:
        return {
            "X-API-Key": self._api_key,
            "X-Client-Version": f"backtest360-client/{self._sdk_version}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, body: dict) -> dict:
        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self._timeout) as http:
            response = http.post(url, headers=self._headers(), content=json.dumps(body))
        _handle_error(response)
        return response.json()

    def _get(self, path: str) -> dict:
        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self._timeout) as http:
            response = http.get(url, headers=self._headers())
        _handle_error(response)
        return response.json()

    # -------------------------------------------------------------------
    # Public transport methods
    # -------------------------------------------------------------------

    def backtest(
        self,
        strategy: Strategy,
        config: BacktestConfig,
        market_data: MarketData,
        benchmark: Optional[MarketData] = None,
    ) -> BacktestResult:
        """Run a backtest and return a BacktestResult."""
        body = _build_backtest_body(strategy, config, market_data, benchmark)
        resp = self._post("/api/backtest", body)
        return BacktestResult.from_dict(resp.get("result", resp))

    def latest_signal(
        self,
        strategy: Strategy,
        config: BacktestConfig,
        market_data: MarketData,
    ) -> LatestSignalResult:
        """Return the latest signal for the given strategy and market data."""
        body = _build_backtest_body(strategy, config, market_data)
        resp = self._post("/api/latest-signal", body)
        return LatestSignalResult.from_dict(resp.get("result", resp))

    def validate_strategy(self, strategy: Strategy) -> ValidationResult:
        """Validate a strategy against the engine's registry without running a backtest."""
        body = strategy.to_dict()
        resp = self._post("/api/validate-strategy", body)
        return ValidationResult.from_dict(resp)

    def list_strategies(self) -> list:
        """Return raw catalog entries from /api/strategies (dicts, not typed)."""
        resp = self._get("/api/strategies")
        return resp if isinstance(resp, list) else resp.get("strategies", [])

    def list_indicators(self) -> list:
        """Return raw catalog entries from /api/indicators (dicts, not typed)."""
        resp = self._get("/api/indicators")
        return resp if isinstance(resp, list) else resp.get("indicators", [])

    def version(self) -> dict:
        """Return engine version info from /api/version."""
        return self._get("/api/version")


# ---------------------------------------------------------------------------
# Request serialization helpers
# ---------------------------------------------------------------------------

def _ohlcv_to_wire(df) -> Optional[dict]:
    """Serialize a DataFrame to pandas split orient with ISO UTC timestamps."""
    if df is None:
        return None
    return {
        "index": [str(ts) for ts in df.index],
        "columns": list(df.columns),
        "data": df.values.tolist(),
    }


def _build_backtest_body(
    strategy: Strategy,
    config: BacktestConfig,
    market_data: MarketData,
    benchmark: Optional[MarketData] = None,
) -> dict:
    body: dict = {
        "strategy": strategy.to_dict(),
        "config": config.to_dict(),
        "market_data": {
            "ohlcv": _ohlcv_to_wire(market_data.ohlcv),
            "asset_info": market_data.asset_info.to_dict(),
            "is_24h": market_data.is_24h,
            "session_open": market_data.session_open,
            "session_close": market_data.session_close,
            "trading_days_per_year": market_data.trading_days_per_year,
            "bar_frequency": market_data.bar_frequency,
            "source_bars_per_year": market_data.source_bars_per_year,
            "missing_bars": market_data.missing_bars,
            "bad_prices": market_data.bad_prices,
            "quality_warnings": market_data.quality_warnings,
        },
    }
    if strategy.precomputed_signals is not None:
        import pandas as pd
        s = strategy.precomputed_signals
        body["strategy"]["precomputed_signals"] = {
            "index": [str(ts) for ts in s.index],
            "data": s.tolist(),
        }
    if benchmark is not None:
        body["benchmark_market_data"] = {
            "ohlcv": _ohlcv_to_wire(benchmark.ohlcv),
        }
    return body
