"""SDK exception hierarchy."""

from __future__ import annotations


class BacktestError(Exception):
    """Base class for all Backtest360 SDK exceptions."""


class AuthenticationError(BacktestError):
    """Raised when the API key is missing, invalid, revoked, or lacks required scope.

    Server triggers: missing key, 401 invalid key, 401 revoked, 403 insufficient scope.
    """


class QuotaExceededError(BacktestError):
    """Raised when the daily request quota is exhausted.

    Server trigger: 429 with quota semantics.
    """

    def __init__(self, message: str, used: int | None = None, limit: int | None = None) -> None:
        super().__init__(message)
        self.used = used
        self.limit = limit


class RateLimitError(BacktestError):
    """Raised when the per-hour rate limit is hit.

    Server trigger: 429 with rate-limit semantics.
    """

    def __init__(
        self,
        message: str,
        used: int | None = None,
        limit: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.used = used
        self.limit = limit
        self.retry_after = retry_after


class ValidationError(BacktestError):
    """Raised when the server rejects the strategy or config as invalid.

    Distinct from the engine-internal ``ValidationIssue`` dataclass (which
    describes a single validation finding on the ``ValidationResult`` output DTO).
    """

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []


class EngineError(BacktestError):
    """Raised for server-side errors (5xx) or client version incompatibility (426).

    Catch this as a fallback for unknown future engine error subclasses.
    """

    def __init__(
        self,
        message: str,
        status: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.request_id = request_id
