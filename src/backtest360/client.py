"""Backtest360 SDK — HTTP client and core types."""

from __future__ import annotations


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
