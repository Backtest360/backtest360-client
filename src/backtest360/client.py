"""Backtest360 SDK — HTTP client and core types."""

from __future__ import annotations

import json
import os
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

import httpx
import pandas as pd

if TYPE_CHECKING:
    from backtest360.strategy import Costs, Execution, Risk, Sizing, Strategy

_DEFAULT_BASE_URL = "https://api.backtest360.com"
_TIMEOUT_SECONDS = 300.0


def _sdk_version() -> str:
    try:
        return version("backtest360-client")
    except PackageNotFoundError:
        return "0.0.0.dev"


# ---------------------------------------------------------------------------


class Backtest360Error(Exception):
    """Raised on any non-2xx response from the Backtest360 API.

    Args:
        message: Human-readable description of the error.
        status: HTTP status code returned by the engine (0 for client-side errors).
        code: Machine-readable error code (e.g. ``SDK_NO_API_KEY``).
        body: Parsed response body (dict) or raw text if JSON parsing failed.
        request_id: Value of the ``X-Request-ID`` response header, if present.

    Example:
        >>> try:
        ...     result = client.backtest(strategy, df)
        ... except Backtest360Error as e:
        ...     if e.status == 401:
        ...         print("Invalid API key")
        ...     elif e.status == 429:
        ...         print("Rate limited, retry later")
        ...     else:
        ...         raise
    """

    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: str | None = None,
        body: dict | str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.body = body
        self.request_id = request_id


# ---------------------------------------------------------------------------


class Result:
    """Wraps a ``/api/backtest`` response.

    All properties are derived lazily from the raw response dict.

    Attributes:
        stats: Full statistics dict — 120+ metrics keyed by metric name.
        trades: List of trade dicts, each with ``entry_date``, ``exit_date``,
            ``direction``, ``return_net``, etc.
        equity: Equity curve as a ``pd.Series`` indexed by datetime.
        returns: Net-of-cost log-return series indexed by datetime.
        signals: Signal series (``{-1, 0, 1}``) indexed by datetime.
        raw: The full ``result`` dict — everything the engine returned.

    Example:
        >>> result = client.backtest(strategy, df)
        >>> print(result.stats["Sharpe"])
        >>> result.equity.plot(title="Equity curve")
        >>> for trade in result.trades[:5]:
        ...     print(trade["entry_date"], trade["return_net"])
    """

    def __init__(self, data: dict) -> None:
        self._data = data

    @property
    def stats(self) -> dict:
        """Performance statistics dict (120+ metrics)."""
        return self._data.get("stats", {})

    @property
    def trades(self) -> list[dict]:
        """Trade log — list of dicts with entry/exit date, direction, return."""
        return self._data.get("trades", [])

    @property
    def equity(self) -> pd.Series:
        """Equity curve as a ``pd.Series`` indexed by datetime."""
        series = self._data.get("series", {})
        return pd.Series(
            series.get("equity", []),
            index=pd.to_datetime(series.get("dates", [])),
            name="equity",
        )

    @property
    def returns(self) -> pd.Series:
        """Net-of-cost log-return series indexed by datetime."""
        series = self._data.get("series", {})
        return pd.Series(
            series.get("returns", []),
            index=pd.to_datetime(series.get("dates", [])),
            name="returns",
        )

    @property
    def signals(self) -> pd.Series:
        """Signal series (``{-1, 0, 1}``) indexed by datetime."""
        series = self._data.get("series", {})
        return pd.Series(
            series.get("signals", []),
            index=pd.to_datetime(series.get("dates", [])),
            name="signals",
        )

    @property
    def raw(self) -> dict:
        """Full engine response dict — access any field not exposed as a property."""
        return self._data


# ---------------------------------------------------------------------------


class Client:
    """Synchronous HTTP client for the Backtest360 backtesting API.

    Args:
        api_key: Your Backtest360 API key. Falls back to the
            ``BACKTEST360_API_KEY`` environment variable. Raises
            ``Backtest360Error(code="SDK_NO_API_KEY")`` immediately if neither is set.
        base_url: Engine base URL. Falls back to ``BACKTEST360_ENGINE_URL`` env var,
            then ``https://api.backtest360.com``.
        timeout: Request timeout in seconds. Defaults to 300 (backtests can
            be slow).

    Example:
        >>> import yfinance as yf
        >>> from backtest360 import Client, Strategy
        >>>
        >>> df = yf.download("BTC-USD", period="1y", interval="1d",
        ...     auto_adjust=False, multi_level_index=False, progress=False)
        >>> df.columns = df.columns.str.lower()
        >>>
        >>> result = Client(api_key="b360_live_...").backtest(
        ...     Strategy.rsi_threshold_long(), df
        ... )
        >>> print(result.stats["Sharpe"])
        >>> result.equity.plot(title="Equity curve")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = _TIMEOUT_SECONDS,
    ) -> None:
        resolved_key = api_key or os.environ.get("BACKTEST360_API_KEY", "")
        if not resolved_key:
            raise Backtest360Error(
                "No API key provided. Pass api_key=... or set the "
                "BACKTEST360_API_KEY environment variable. "
                "Sign up at backtest360.com.",
                status=401,
                code="SDK_NO_API_KEY",
            )
        self._api_key = resolved_key
        self._base_url = (
            base_url or os.environ.get("BACKTEST360_ENGINE_URL") or _DEFAULT_BASE_URL
        ).rstrip("/")
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "X-Client-Version": f"backtest360-client/{_sdk_version()}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        """Send an HTTP request and return the parsed JSON response.

        Raises:
            Backtest360Error: On any non-2xx response or a forbidden path.
        """
        if not path.startswith("/api/"):
            raise Backtest360Error(
                f"Path '{path}' is not permitted. SDK only accesses /api/* endpoints.",
                status=0,
                code="SDK_PATH_FORBIDDEN",
            )
        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self._timeout) as http:
            if method == "GET":
                response = http.get(url, headers=self._headers())
            else:
                response = http.post(
                    url,
                    headers=self._headers(),
                    content=json.dumps(body or {}),
                )

        if response.status_code >= 400:
            try:
                resp_body: dict | str | None = response.json()
            except Exception:
                resp_body = response.text or None

            request_id = response.headers.get("x-request-id")

            if isinstance(resp_body, dict):
                detail = resp_body.get("detail", {})
                if isinstance(detail, str):
                    message = detail
                elif isinstance(detail, dict):
                    message = detail.get("message", "") or response.text
                else:
                    message = response.text
            else:
                message = str(resp_body) if resp_body else ""

            raise Backtest360Error(
                message or f"HTTP {response.status_code}",
                status=response.status_code,
                body=resp_body,
                request_id=request_id,
            )

        return response.json()

    # ---------------------------------------------------------------------------
    # Public API methods
    # ---------------------------------------------------------------------------

    def version(self) -> dict:
        """Return engine version info from ``GET /api/version``.

        Returns:
            Dict with at minimum ``{"version": "x.y.z"}``. May include
            ``min_client``, ``api_contract``, and ``latest_client`` fields.

        Raises:
            Backtest360Error: On any non-2xx response.

        Example:
            >>> info = client.version()
            >>> print(info["version"])
            0.5.3
        """
        return self._request("GET", "/api/version")

    def list_indicators(self) -> list[dict]:
        """Return the engine's indicator library from ``GET /api/indicators``.

        Each entry describes an indicator's name, parameters, kind, and output
        columns. Use this to discover available indicators and their parameter
        schemas when building custom strategies.

        See also: https://api.backtest360.com/docs#tag/Reference

        Returns:
            List of indicator descriptor dicts.

        Raises:
            Backtest360Error: On any non-2xx response.

        Example:
            >>> for ind in client.list_indicators():
            ...     print(ind["name"], ind.get("params", {}).keys())
        """
        resp = self._request("GET", "/api/indicators")
        return resp if isinstance(resp, list) else resp.get("indicators", [])

    def list_strategies(self) -> list[dict]:
        """Return the engine's built-in strategy templates from ``GET /api/strategies``.

        Each entry carries the strategy's ``name``, ``description``,
        ``condition_tree``, and ``indicators``.

        See also: https://api.backtest360.com/docs#tag/Reference

        Returns:
            List of strategy descriptor dicts.

        Raises:
            Backtest360Error: On any non-2xx response.

        Example:
            >>> for s in client.list_strategies():
            ...     print(s["name"], s["description"])
        """
        resp = self._request("GET", "/api/strategies")
        return resp if isinstance(resp, list) else resp.get("strategies", [])

    def validate_strategy(self, strategy: Strategy) -> dict:
        """Validate a strategy against the engine's registry without running a backtest.

        Args:
            strategy: A :class:`~backtest360.Strategy` instance to validate.

        Returns:
            Validation result dict with ``is_valid``, ``errors``, and
            ``warnings`` fields.

        Raises:
            Backtest360Error: On HTTP error.

        Example:
            >>> v = client.validate_strategy(Strategy.rsi_threshold_long())
            >>> print(v["is_valid"], v.get("errors", []))
        """
        return self._request("POST", "/api/validate-strategy", strategy.to_wire())

    def latest_signal(
        self,
        strategy: Strategy,
        ohlcv: pd.DataFrame,
        *,
        execution: Execution | None = None,
        costs: Costs | None = None,
        risk: Risk | None = None,
        sizing: Sizing | None = None,
    ) -> dict:
        """Return the latest signal for a strategy on the given data.

        Uses ``POST /api/latest-signal``. Returns only the most-recent bar's
        signal and per-condition diagnostics — no P&L or statistics.

        Args:
            strategy: Strategy definition.
            ohlcv: DataFrame indexed by datetime with columns
                ``open/high/low/close/volume``.
            execution: Execution configuration (optional).
            costs: Cost configuration (optional).
            risk: Risk / stop configuration (optional).
            sizing: Position sizing configuration (optional).

        Returns:
            Dict with ``signal`` (int), ``long_entry_fired`` (bool), and
            related diagnostic fields.

        Raises:
            Backtest360Error: On HTTP error or invalid strategy.

        Example:
            >>> sig = client.latest_signal(Strategy.rsi_threshold_long(), df)
            >>> print(sig["signal"])  # -1 / 0 / 1
        """
        body = _build_backtest_body(strategy, ohlcv, None, execution, costs, risk, sizing)
        return self._request("POST", "/api/latest-signal", body)

    def backtest_raw(self, payload: dict) -> dict:
        """Send a raw ``POST /api/backtest`` payload, return the raw response dict.

        For users who want exact control over the wire format — build the JSON
        payload yourself with the API docs open.

        Args:
            payload: Dict matching the ``/api/backtest`` request body exactly.
                     See https://api.backtest360.com/docs for the full schema.

        Returns:
            The full response dict from the engine (``result`` key and all).

        Raises:
            Backtest360Error: On any non-2xx response.

        Example:
            >>> resp = client.backtest_raw({
            ...     "strategy": {"condition_tree": {...}, "indicators": [...]},
            ...     "data_source": {"ohlcv": {...}},
            ...     "execution": {"signal_frequency": "daily"},
            ... })
        """
        return self._request("POST", "/api/backtest", payload)

    def backtest(
        self,
        strategy: Strategy,
        ohlcv: pd.DataFrame,
        *,
        benchmark: pd.DataFrame | None = None,
        execution: Execution | None = None,
        costs: Costs | None = None,
        risk: Risk | None = None,
        sizing: Sizing | None = None,
    ) -> Result:
        """Run a historical backtest and return a :class:`Result`.

        Args:
            strategy: Strategy definition. Use a template (e.g.
                ``Strategy.rsi_threshold_long()``) or build your own.
            ohlcv: DataFrame indexed by datetime with lowercase columns
                ``open``, ``high``, ``low``, ``close`` (and optionally
                ``volume``).
            benchmark: Optional benchmark DataFrame (same shape as ``ohlcv``).
                When provided, the engine adds Alpha, Beta, Information Ratio,
                Tracking Error, Up/Down Capture to ``result.stats``.
            execution: Execution timing config — ``entry``, ``exit``,
                ``signal_frequency``, etc.
            costs: Transaction costs — ``slippage_bps``, ``fee_pct``, etc.
            risk: Stop-loss / drawdown protection config.
            sizing: Position sizing config.

        Returns:
            A :class:`Result` wrapping the engine response.

        Raises:
            Backtest360Error: On any non-2xx response.

        Example:
            >>> from backtest360 import Client, Strategy, Execution, Costs
            >>> result = Client(api_key="...").backtest(
            ...     Strategy.rsi_threshold_long(), df,
            ...     execution=Execution(signal_frequency="daily"),
            ...     costs=Costs(slippage_bps=2.5, fee_pct=0.001),
            ... )
            >>> print(result.stats["Sharpe"])
            >>> result.equity.plot()
        """
        body = _build_backtest_body(strategy, ohlcv, benchmark, execution, costs, risk, sizing)
        resp = self._request("POST", "/api/backtest", body)
        result_data = resp.get("result", resp)
        return Result(result_data)


# ---------------------------------------------------------------------------
# Wire serialisation helpers
# ---------------------------------------------------------------------------


def _ohlcv_to_wire(df: pd.DataFrame) -> dict:
    """Serialise a DataFrame to the engine's parallel-array OHLCV format."""
    result: dict = {
        "dates": [str(ts) for ts in df.index],
        "open":  df["open"].tolist(),
        "high":  df["high"].tolist(),
        "low":   df["low"].tolist(),
        "close": df["close"].tolist(),
    }
    if "volume" in df.columns:
        result["volume"] = df["volume"].tolist()
    return result


def _build_execution_wire(
    execution: Execution | None,
    costs: Costs | None,
    risk: Risk | None,
    sizing: Sizing | None,
) -> dict:
    """Merge the grouped-knob objects into the engine's flat execution dict."""
    d: dict = {}
    if execution is not None:
        d.update(execution.to_wire())
    if costs is not None:
        d.update(costs.to_wire())
    if risk is not None:
        d.update(risk.to_wire())
    if sizing is not None:
        d.update(sizing.to_wire())
    return d


def _build_backtest_body(
    strategy: Strategy,
    ohlcv: pd.DataFrame,
    benchmark: pd.DataFrame | None,
    execution: Execution | None,
    costs: Costs | None,
    risk: Risk | None,
    sizing: Sizing | None,
) -> dict:
    body: dict = {
        "data_source": {"ohlcv": _ohlcv_to_wire(ohlcv)},
        "strategy": strategy.to_wire(),
    }
    exec_wire = _build_execution_wire(execution, costs, risk, sizing)
    if exec_wire:
        body["execution"] = exec_wire
    if benchmark is not None:
        body["benchmark"] = {"ohlcv": _ohlcv_to_wire(benchmark)}
    return body
