"""Unit tests for exceptions.py — one instantiation + str() test per class."""

import pytest

from backtest360.exceptions import (
    AuthenticationError,
    BacktestError,
    EngineError,
    QuotaExceededError,
    RateLimitError,
    ValidationError,
)


def test_authentication_error_is_backtest_error():
    exc = AuthenticationError("Invalid API key.")
    assert isinstance(exc, BacktestError)
    assert str(exc) == "Invalid API key."


def test_authentication_error_scope_message():
    msg = "Your key lacks the required scope for this endpoint."
    exc = AuthenticationError(msg)
    assert str(exc) == msg


def test_quota_exceeded_error_str():
    exc = QuotaExceededError("Daily quota exceeded (100/100).", used=100, limit=100)
    assert str(exc) == "Daily quota exceeded (100/100)."
    assert exc.used == 100
    assert exc.limit == 100


def test_quota_exceeded_error_no_counts():
    exc = QuotaExceededError("Quota exceeded.")
    assert exc.used is None
    assert exc.limit is None


def test_rate_limit_error_str():
    exc = RateLimitError("Rate limit hit (10/10 per hour).", used=10, limit=10, retry_after=42)
    assert str(exc) == "Rate limit hit (10/10 per hour)."
    assert exc.retry_after == 42


def test_rate_limit_error_no_retry():
    exc = RateLimitError("Rate limit hit.")
    assert exc.retry_after is None


def test_validation_error_str():
    exc = ValidationError("Strategy is invalid.", issues=["RSI lookback must be > 0"])
    assert str(exc) == "Strategy is invalid."
    assert exc.issues == ["RSI lookback must be > 0"]


def test_validation_error_no_issues():
    exc = ValidationError("Strategy is invalid.")
    assert exc.issues == []


def test_engine_error_str():
    exc = EngineError("Service error.", status=500, request_id="req-abc-123")
    assert str(exc) == "Service error."
    assert exc.status == 500
    assert exc.request_id == "req-abc-123"


def test_engine_error_no_extras():
    exc = EngineError("Unexpected error.")
    assert exc.status is None
    assert exc.request_id is None


def test_all_exceptions_are_subclass_of_backtest_error():
    for cls in (AuthenticationError, QuotaExceededError, RateLimitError, ValidationError, EngineError):
        assert issubclass(cls, BacktestError), f"{cls.__name__} must subclass BacktestError"


def test_can_catch_as_exception():
    with pytest.raises(BacktestError):
        raise AuthenticationError("test")

    with pytest.raises(BacktestError):
        raise QuotaExceededError("test")

    with pytest.raises(BacktestError):
        raise RateLimitError("test")

    with pytest.raises(BacktestError):
        raise ValidationError("test")

    with pytest.raises(BacktestError):
        raise EngineError("test")
