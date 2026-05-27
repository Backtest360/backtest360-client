"""Backtest360 SDK — HTTP client and core types."""

from __future__ import annotations

import json
import os
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import httpx

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
        status: HTTP status code returned by the engine.
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
        body: dict | str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body
        self.request_id = request_id


# ---------------------------------------------------------------------------


class Client:
    """Synchronous HTTP client for the Backtest360 backtesting API.

    Args:
        api_key: Your Backtest360 API key. Falls back to the
            ``BACKTEST360_API_KEY`` environment variable. Raises
            ``Backtest360Error(status=401)`` immediately if neither is set.
        base_url: Engine base URL. Defaults to ``https://api.backtest360.com``.
        timeout: Request timeout in seconds. Defaults to 300 (backtests can
            be slow).

    Example:
        >>> from backtest360 import Client, Strategy
        >>> client = Client(api_key="b360_live_...")
        >>> result = client.backtest(Strategy.rsi_threshold_long(), df)
        >>> print(result.stats["sharpe_ratio"])
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _TIMEOUT_SECONDS,
    ) -> None:
        resolved = api_key or os.environ.get("BACKTEST360_API_KEY", "")
        if not resolved:
            raise Backtest360Error(
                "No API key provided. Pass api_key=... or set the "
                "BACKTEST360_API_KEY environment variable. "
                "Sign up at backtest360.com.",
                status=401,
            )
        self._api_key = resolved
        self._base_url = base_url.rstrip("/")
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
            Backtest360Error: On any non-2xx response.
        """
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
