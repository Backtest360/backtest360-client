"""Unit tests for BacktestClient — all httpx calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backtest360.client import BacktestClient, _handle_error, _ohlcv_to_wire, _resolve_api_key
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, body: object = None, headers: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(body) if body else ""
    resp.headers = headers or {}
    if body is not None:
        resp.json.return_value = body
    else:
        resp.json.side_effect = Exception("no body")
    return resp


def _client(api_key: str = "b360_test_key") -> BacktestClient:
    return BacktestClient(api_key=api_key)


# ---------------------------------------------------------------------------
# _resolve_api_key
# ---------------------------------------------------------------------------


def test_resolve_api_key_explicit():
    assert _resolve_api_key("explicit_key") == "explicit_key"


def test_resolve_api_key_env(monkeypatch):
    monkeypatch.setenv("BACKTEST360_API_KEY", "env_key")
    assert _resolve_api_key(None) == "env_key"


def test_resolve_api_key_raises_without_key(monkeypatch):
    monkeypatch.delenv("BACKTEST360_API_KEY", raising=False)
    with pytest.raises(AuthenticationError):
        _resolve_api_key(None)


# ---------------------------------------------------------------------------
# _handle_error — error mapping table
# ---------------------------------------------------------------------------


def test_handle_error_passthrough_on_2xx():
    _handle_error(_mock_response(200, {"ok": True}))  # no raise


def test_handle_error_401():
    with pytest.raises(AuthenticationError):
        _handle_error(_mock_response(401, {"detail": "bad key"}))


def test_handle_error_403():
    with pytest.raises(AuthenticationError):
        _handle_error(_mock_response(403, {"detail": "insufficient scope"}))


def test_handle_error_422_string_detail():
    resp = _mock_response(422, {"detail": "Strategy is invalid."})
    with pytest.raises(ValidationError):
        _handle_error(resp)


def test_handle_error_422_list_detail():
    body = {"detail": [{"msg": "field required", "loc": ["strategy"]}]}
    resp = _mock_response(422, body)
    with pytest.raises(ValidationError) as exc_info:
        _handle_error(resp)
    assert "field required" in exc_info.value.issues


def test_handle_error_426():
    body = {"detail": {"message": "upgrade client", "code": "UPGRADE_REQUIRED"}}
    resp = _mock_response(426, body)
    with pytest.raises(EngineError) as exc_info:
        _handle_error(resp)
    assert exc_info.value.status == 426


def test_handle_error_429_quota():
    body = {
        "detail": {"message": "quota exceeded", "code": "QUOTA_EXCEEDED"},
        "used": 100,
        "limit": 50,
    }
    resp = _mock_response(429, body)
    with pytest.raises(QuotaExceededError) as exc_info:
        _handle_error(resp)
    assert exc_info.value.used == 100
    assert exc_info.value.limit == 50


def test_handle_error_429_rate_limit():
    body = {"detail": {"message": "too many requests", "code": "RATE_LIMITED"}}
    resp = _mock_response(429, body, headers={"Retry-After": "30"})
    with pytest.raises(RateLimitError) as exc_info:
        _handle_error(resp)
    assert exc_info.value.retry_after == 30


def test_handle_error_500():
    body = {"detail": {"message": "internal error", "code": "INTERNAL"}}
    resp = _mock_response(500, body, headers={"x-request-id": "abc-123"})
    with pytest.raises(EngineError) as exc_info:
        _handle_error(resp)
    assert exc_info.value.status == 500
    assert exc_info.value.request_id == "abc-123"


def test_handle_error_no_body():
    resp = _mock_response(503)
    with pytest.raises(EngineError):
        _handle_error(resp)


# ---------------------------------------------------------------------------
# _ohlcv_to_wire
# ---------------------------------------------------------------------------


def test_ohlcv_to_wire_none():
    assert _ohlcv_to_wire(None) is None


def test_ohlcv_to_wire_dataframe():
    import pandas as pd

    idx = pd.to_datetime(["2024-01-01", "2024-01-02"])
    df = pd.DataFrame({"open": [1.0, 2.0], "close": [1.1, 2.1]}, index=idx)
    result = _ohlcv_to_wire(df)
    assert result["columns"] == ["open", "close"]
    assert len(result["index"]) == 2
    assert len(result["data"]) == 2


# ---------------------------------------------------------------------------
# BacktestClient — header contract
# ---------------------------------------------------------------------------


def test_headers_contain_api_key():
    c = _client("b360_test_abc")
    h = c._headers()
    assert h["X-API-Key"] == "b360_test_abc"


def test_headers_contain_client_version():
    c = _client()
    h = c._headers()
    assert h["X-Client-Version"].startswith("backtest360-client/")


def test_headers_contain_content_type():
    c = _client()
    assert c._headers()["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# BacktestClient.backtest
# ---------------------------------------------------------------------------


def _minimal_market_data() -> MarketData:
    import pandas as pd

    idx = pd.to_datetime(["2024-01-01", "2024-01-02"])
    df = pd.DataFrame(
        {
            "open": [1.0, 2.0],
            "high": [1.2, 2.2],
            "low": [0.9, 1.9],
            "close": [1.1, 2.1],
            "volume": [1000, 2000],
        },
        index=idx,
    )
    md = MarketData()
    md.ohlcv = df
    return md


def _backtest_result_body() -> dict:
    return {
        "result": {
            "run_result": {
                "trades": [],
                "signal_bars_per_year": 252,
                "returns": {"index": [], "data": []},
                "signals": {"index": [], "data": []},
            },
            "stats": {},
            "signal_diagnostics": {},
        }
    }


def test_backtest_calls_post_endpoint():
    c = _client()
    body = _backtest_result_body()
    with patch.object(c, "_post", return_value=body["result"]) as mock_post:
        result = c.backtest(Strategy(), BacktestConfig(), _minimal_market_data())
    mock_post.assert_called_once()
    assert mock_post.call_args[0][0] == "/api/backtest"
    assert isinstance(result, BacktestResult)


def test_backtest_with_benchmark():
    c = _client()
    body = _backtest_result_body()
    with patch.object(c, "_post", return_value=body["result"]) as mock_post:
        c.backtest(
            Strategy(), BacktestConfig(), _minimal_market_data(), benchmark=_minimal_market_data()
        )
    posted_body = mock_post.call_args[0][1]
    assert "benchmark" in posted_body


# ---------------------------------------------------------------------------
# BacktestClient.latest_signal
# ---------------------------------------------------------------------------


def _latest_signal_body() -> dict:
    return {
        "result": {
            "signal": 1,
            "bar_timestamp": "2024-01-02T00:00:00",
            "long_entry_fired": True,
            "long_exit_fired": False,
            "short_entry_fired": False,
            "short_exit_fired": False,
            "warmup_bars_used": 14,
            "created_at": "2024-01-02T12:00:00",
        }
    }


def test_latest_signal_calls_post_endpoint():
    c = _client()
    with patch.object(c, "_post", return_value=_latest_signal_body()["result"]) as mock_post:
        result = c.latest_signal(Strategy(), BacktestConfig(), _minimal_market_data())
    mock_post.assert_called_once()
    assert mock_post.call_args[0][0] == "/api/latest-signal"
    assert isinstance(result, LatestSignalResult)


# ---------------------------------------------------------------------------
# BacktestClient.validate_strategy
# ---------------------------------------------------------------------------


def test_validate_strategy_calls_post_endpoint():
    c = _client()
    resp = {"valid": True, "issues": []}
    with patch.object(c, "_post", return_value=resp) as mock_post:
        result = c.validate_strategy(Strategy())
    mock_post.assert_called_once()
    assert mock_post.call_args[0][0] == "/api/validate-strategy"
    assert isinstance(result, ValidationResult)
    assert result.valid is True


# ---------------------------------------------------------------------------
# BacktestClient.list_strategies
# ---------------------------------------------------------------------------


def test_list_strategies_returns_list():
    c = _client()
    with patch.object(c, "_get", return_value=[{"name": "rsi_long"}]):
        result = c.list_strategies()
    assert result == [{"name": "rsi_long"}]


def test_list_strategies_unwraps_dict_response():
    c = _client()
    with patch.object(c, "_get", return_value={"strategies": [{"name": "rsi_long"}]}):
        result = c.list_strategies()
    assert result == [{"name": "rsi_long"}]


# ---------------------------------------------------------------------------
# BacktestClient.list_indicators
# ---------------------------------------------------------------------------


def test_list_indicators_returns_list():
    c = _client()
    with patch.object(c, "_get", return_value=[{"id": "rsi"}]):
        result = c.list_indicators()
    assert result == [{"id": "rsi"}]


def test_list_indicators_unwraps_dict_response():
    c = _client()
    with patch.object(c, "_get", return_value={"indicators": [{"id": "rsi"}]}):
        result = c.list_indicators()
    assert result == [{"id": "rsi"}]


# ---------------------------------------------------------------------------
# BacktestClient.version
# ---------------------------------------------------------------------------


def test_version_calls_get_endpoint():
    c = _client()
    with patch.object(c, "_get", return_value={"engine": "0.5.3"}) as mock_get:
        result = c.version()
    mock_get.assert_called_once_with("/version")
    assert result == {"engine": "0.5.3"}


# ---------------------------------------------------------------------------
# BacktestClient._post / _get — httpx integration (one real mock-httpx call)
# ---------------------------------------------------------------------------


def test_post_sends_json_body():
    c = _client()
    fake_resp = _mock_response(200, {"result": {}})
    with patch("backtest360.client.httpx.Client") as mock_client_cls:
        ctx = mock_client_cls.return_value.__enter__.return_value
        ctx.post.return_value = fake_resp
        result = c._post("/api/test", {"key": "value"})
    ctx.post.assert_called_once()
    call_kwargs = ctx.post.call_args
    assert call_kwargs[1]["content"] == json.dumps({"key": "value"})
    assert result == {"result": {}}


def test_get_sends_headers():
    c = _client("b360_hdr_test")
    fake_resp = _mock_response(200, {"version": "1"})
    with patch("backtest360.client.httpx.Client") as mock_client_cls:
        ctx = mock_client_cls.return_value.__enter__.return_value
        ctx.get.return_value = fake_resp
        c._get("/api/version")
    call_kwargs = ctx.get.call_args
    assert call_kwargs[1]["headers"]["X-API-Key"] == "b360_hdr_test"


def test_post_raises_on_error_status():
    c = _client()
    fake_resp = _mock_response(401, {"detail": "bad key"})
    with patch("backtest360.client.httpx.Client") as mock_client_cls:
        ctx = mock_client_cls.return_value.__enter__.return_value
        ctx.post.return_value = fake_resp
        with pytest.raises(AuthenticationError):
            c._post("/api/backtest", {})
