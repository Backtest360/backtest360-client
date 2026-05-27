"""Tests for Backtest360Error, Client, and Result."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backtest360.client import (
    Backtest360Error,
    Client,
    Result,
    _build_execution_wire,
    _ohlcv_to_wire,
)
from backtest360.strategy import Costs, Execution, Risk, Sizing, Strategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_http_context(method: str, status: int, json_body=None, text: str = "", headers=None):
    """Return a patched httpx.Client context manager yielding a mock response."""
    response = MagicMock()
    response.status_code = status
    if json_body is not None:
        response.json.return_value = json_body
    else:
        response.json.side_effect = Exception("not JSON")
    response.text = text
    response.headers = headers or {}

    mock_http = MagicMock()
    if method == "GET":
        mock_http.get.return_value = response
    else:
        mock_http.post.return_value = response

    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_http)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx, mock_http, response


# ---------------------------------------------------------------------------
# Backtest360Error tests
# ---------------------------------------------------------------------------


def test_message_and_status():
    e = Backtest360Error("bad key", status=401)
    assert str(e) == "bad key"
    assert e.status == 401


def test_body_and_request_id_defaults_to_none():
    e = Backtest360Error("error", status=500)
    assert e.body is None
    assert e.request_id is None


def test_body_dict():
    body = {"detail": {"message": "quota exhausted", "code": "QUOTA_EXCEEDED"}}
    e = Backtest360Error("quota exhausted", status=429, body=body)
    assert e.body == body
    assert e.status == 429


def test_body_str():
    e = Backtest360Error("gateway timeout", status=504, body="<html>502</html>")
    assert e.body == "<html>502</html>"


def test_request_id():
    e = Backtest360Error("server error", status=500, request_id="req-abc-123")
    assert e.request_id == "req-abc-123"


def test_all_fields():
    e = Backtest360Error(
        "rate limited",
        status=429,
        body={"detail": "too many requests"},
        request_id="req-xyz",
    )
    assert str(e) == "rate limited"
    assert e.status == 429
    assert e.body == {"detail": "too many requests"}
    assert e.request_id == "req-xyz"


def test_is_exception_subclass():
    assert issubclass(Backtest360Error, Exception)


def test_raise_and_catch():
    with pytest.raises(Backtest360Error) as exc_info:
        raise Backtest360Error("unauthorized", status=401)
    assert exc_info.value.status == 401


def test_catch_as_base_exception():
    with pytest.raises(Backtest360Error):
        raise Backtest360Error("error", status=500)


def test_importable_from_package():
    from backtest360 import Backtest360Error as E  # noqa: F401

    assert E is Backtest360Error


# ---------------------------------------------------------------------------
# Client.__init__ tests
# ---------------------------------------------------------------------------


def test_client_init_explicit_key():
    c = Client(api_key="b360_live_testkey")
    assert c._api_key == "b360_live_testkey"


def test_client_init_from_env(monkeypatch):
    monkeypatch.setenv("BACKTEST360_API_KEY", "b360_env_key")
    c = Client()
    assert c._api_key == "b360_env_key"


def test_client_explicit_key_takes_priority(monkeypatch):
    monkeypatch.setenv("BACKTEST360_API_KEY", "env_key")
    c = Client(api_key="explicit_key")
    assert c._api_key == "explicit_key"


def test_client_no_key_raises(monkeypatch):
    monkeypatch.delenv("BACKTEST360_API_KEY", raising=False)
    with pytest.raises(Backtest360Error) as exc_info:
        Client()
    assert exc_info.value.status == 401
    assert "API key" in str(exc_info.value)


def test_client_empty_env_key_raises(monkeypatch):
    monkeypatch.setenv("BACKTEST360_API_KEY", "")
    with pytest.raises(Backtest360Error) as exc_info:
        Client()
    assert exc_info.value.status == 401


def test_client_default_base_url():
    c = Client(api_key="key")
    assert c._base_url == "https://api.backtest360.com"


def test_client_custom_base_url():
    c = Client(api_key="key", base_url="http://localhost:8000/")
    assert c._base_url == "http://localhost:8000"  # trailing slash stripped


def test_client_custom_timeout():
    c = Client(api_key="key", timeout=60.0)
    assert c._timeout == 60.0


def test_client_headers_contain_api_key():
    c = Client(api_key="my_key")
    headers = c._headers()
    assert headers["X-API-Key"] == "my_key"
    assert "X-Client-Version" in headers
    assert "backtest360-client/" in headers["X-Client-Version"]
    assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# Client._request tests
# ---------------------------------------------------------------------------


def test_request_get_happy_path():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("GET", 200, {"version": "1.0"})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c._request("GET", "/version")
    assert result == {"version": "1.0"}
    mock_http.get.assert_called_once()
    call_url = mock_http.get.call_args[0][0]
    assert call_url == "https://api.backtest360.com/version"


def test_request_post_happy_path():
    c = Client(api_key="key")
    resp_body = {"result": {"sharpe_ratio": 1.5}}
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, resp_body)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c._request("POST", "/api/backtest", {"strategy": {}})
    assert result == resp_body
    mock_http.post.assert_called_once()


def test_request_post_sends_json_body():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, {})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c._request("POST", "/api/backtest", {"key": "value"})
    _, call_kwargs = mock_http.post.call_args
    sent = json.loads(call_kwargs["content"])
    assert sent == {"key": "value"}


def test_request_401_raises_backtest360error():
    c = Client(api_key="bad_key")
    body = {"detail": "Invalid API key."}
    mock_ctx, _, _ = _mock_http_context("GET", 401, body)
    patcher = patch("backtest360.client.httpx.Client", return_value=mock_ctx)
    with patcher, pytest.raises(Backtest360Error) as exc_info:
        c._request("GET", "/version")
    assert exc_info.value.status == 401
    assert exc_info.value.body == body


def test_request_429_raises_with_status_and_body():
    c = Client(api_key="key")
    body = {"detail": {"message": "Rate limit exceeded.", "code": "RATE_LIMITED"}}
    mock_ctx, _, _ = _mock_http_context("GET", 429, body)
    patcher = patch("backtest360.client.httpx.Client", return_value=mock_ctx)
    with patcher, pytest.raises(Backtest360Error) as exc_info:
        c._request("GET", "/api/backtest")
    assert exc_info.value.status == 429
    assert exc_info.value.body == body


def test_request_500_raises():
    c = Client(api_key="key")
    body = {"detail": "Internal server error."}
    mock_ctx, _, _ = _mock_http_context("GET", 500, body)
    patcher = patch("backtest360.client.httpx.Client", return_value=mock_ctx)
    with patcher, pytest.raises(Backtest360Error) as exc_info:
        c._request("GET", "/api/backtest")
    assert exc_info.value.status == 500


def test_request_non_json_body_stored_as_string():
    c = Client(api_key="key")
    mock_ctx, _, _ = _mock_http_context("GET", 502, text="<html>Bad Gateway</html>")
    patcher = patch("backtest360.client.httpx.Client", return_value=mock_ctx)
    with patcher, pytest.raises(Backtest360Error) as exc_info:
        c._request("GET", "/version")
    assert exc_info.value.status == 502
    assert exc_info.value.body == "<html>Bad Gateway</html>"


def test_request_propagates_request_id_header():
    c = Client(api_key="key")
    body = {"detail": "Not found."}
    headers = {"x-request-id": "req-abc-999"}
    mock_ctx, _, _ = _mock_http_context("GET", 404, body, headers=headers)
    patcher = patch("backtest360.client.httpx.Client", return_value=mock_ctx)
    with patcher, pytest.raises(Backtest360Error) as exc_info:
        c._request("GET", "/api/whatever")
    assert exc_info.value.request_id == "req-abc-999"


def test_client_importable_from_package():
    from backtest360 import Client as C  # noqa: F401

    assert C is Client


# ---------------------------------------------------------------------------
# Client.version tests
# ---------------------------------------------------------------------------


def test_version_returns_dict():
    c = Client(api_key="key")
    payload = {"version": "0.5.3", "min_client": "0.1.0a1"}
    mock_ctx, mock_http, _ = _mock_http_context("GET", 200, payload)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.version()
    assert result == payload


def test_version_hits_correct_path():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("GET", 200, {"version": "1.0"})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.version()
    call_url = mock_http.get.call_args[0][0]
    assert call_url.endswith("/version")


def test_version_passes_through_raw_dict():
    c = Client(api_key="key")
    payload = {"version": "0.5.3", "api_contract": "2026-05-27", "latest_client": "0.1.0a1"}
    mock_ctx, _, _ = _mock_http_context("GET", 200, payload)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.version()
    assert result["api_contract"] == "2026-05-27"
    assert result["latest_client"] == "0.1.0a1"


def test_version_propagates_error():
    c = Client(api_key="key")
    mock_ctx, _, _ = _mock_http_context("GET", 401, {"detail": "Invalid key."})
    patcher = patch("backtest360.client.httpx.Client", return_value=mock_ctx)
    with patcher, pytest.raises(Backtest360Error) as exc_info:
        c.version()
    assert exc_info.value.status == 401


# ---------------------------------------------------------------------------
# Client.list_indicators / list_strategies
# ---------------------------------------------------------------------------


def test_list_indicators_list_response():
    c = Client(api_key="key")
    payload = [{"name": "rsi"}, {"name": "sma"}]
    mock_ctx, _, _ = _mock_http_context("GET", 200, payload)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.list_indicators()
    assert result == payload


def test_list_indicators_wrapped_response():
    c = Client(api_key="key")
    payload = {"indicators": [{"name": "rsi"}], "total": 1}
    mock_ctx, _, _ = _mock_http_context("GET", 200, payload)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.list_indicators()
    assert result == [{"name": "rsi"}]


def test_list_indicators_empty():
    c = Client(api_key="key")
    mock_ctx, _, _ = _mock_http_context("GET", 200, [])
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.list_indicators()
    assert result == []


def test_list_strategies_list_response():
    c = Client(api_key="key")
    payload = [{"name": "rsi_threshold_long"}, {"name": "ma_crossover"}]
    mock_ctx, _, _ = _mock_http_context("GET", 200, payload)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.list_strategies()
    assert result == payload


def test_list_strategies_wrapped_response():
    c = Client(api_key="key")
    payload = {"strategies": [{"name": "rsi_threshold_long"}]}
    mock_ctx, _, _ = _mock_http_context("GET", 200, payload)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.list_strategies()
    assert result == [{"name": "rsi_threshold_long"}]


def test_list_indicators_correct_path():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("GET", 200, [])
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.list_indicators()
    assert mock_http.get.call_args[0][0].endswith("/api/indicators")


def test_list_strategies_correct_path():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("GET", 200, [])
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.list_strategies()
    assert mock_http.get.call_args[0][0].endswith("/api/strategies")


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

_FIXTURE_RESULT = {
    "stats": {"Sharpe": 1.42, "CAGR": 0.089},
    "series": {
        "dates":   ["2020-01-02", "2020-01-03", "2020-01-04"],
        "equity":  [1.0, 1.01, 1.02],
        "returns": [0.0, 0.01, 0.01],
        "signals": [0, 1, 1],
    },
    "trades": [
        {"entry_date": "2020-01-03", "exit_date": "2020-01-04",
         "direction": 1, "return_net": 0.01},
    ],
    "monthly_returns": [{"period": "2020-01-31", "return": 0.02}],
}


def test_result_stats():
    r = Result(_FIXTURE_RESULT)
    assert r.stats["Sharpe"] == 1.42
    assert r.stats["CAGR"] == 0.089


def test_result_trades():
    r = Result(_FIXTURE_RESULT)
    assert len(r.trades) == 1
    assert r.trades[0]["direction"] == 1
    assert r.trades[0]["return_net"] == 0.01


def test_result_equity_is_series():
    r = Result(_FIXTURE_RESULT)
    eq = r.equity
    assert isinstance(eq, pd.Series)
    assert len(eq) == 3
    assert eq.iloc[0] == 1.0
    assert eq.iloc[-1] == 1.02
    assert eq.name == "equity"


def test_result_equity_datetime_index():
    r = Result(_FIXTURE_RESULT)
    assert r.equity.index.dtype == "datetime64[ns]"


def test_result_returns_is_series():
    r = Result(_FIXTURE_RESULT)
    ret = r.returns
    assert isinstance(ret, pd.Series)
    assert ret.name == "returns"
    assert list(ret.values) == [0.0, 0.01, 0.01]


def test_result_signals_is_series():
    r = Result(_FIXTURE_RESULT)
    sig = r.signals
    assert isinstance(sig, pd.Series)
    assert sig.name == "signals"
    assert list(sig.values) == [0, 1, 1]


def test_result_raw():
    r = Result(_FIXTURE_RESULT)
    assert r.raw is _FIXTURE_RESULT
    assert "monthly_returns" in r.raw


def test_result_empty_series_fields():
    r = Result({"stats": {}, "trades": []})
    assert r.equity.empty
    assert r.returns.empty
    assert r.signals.empty


def test_result_importable_from_package():
    from backtest360 import Result as R  # noqa: F401
    assert R is Result


# ---------------------------------------------------------------------------
# _ohlcv_to_wire
# ---------------------------------------------------------------------------


def _make_df(n=3):
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "open":  [1.0] * n,
        "high":  [1.1] * n,
        "low":   [0.9] * n,
        "close": [1.05] * n,
        "volume": [1000.0] * n,
    }, index=idx)


def test_ohlcv_to_wire_keys():
    df = _make_df()
    w = _ohlcv_to_wire(df)
    assert "dates" in w
    assert "open" in w
    assert "high" in w
    assert "low" in w
    assert "close" in w
    assert "volume" in w


def test_ohlcv_to_wire_no_volume():
    df = _make_df().drop(columns=["volume"])
    w = _ohlcv_to_wire(df)
    assert "volume" not in w


def test_ohlcv_to_wire_dates_are_strings():
    df = _make_df()
    w = _ohlcv_to_wire(df)
    assert all(isinstance(d, str) for d in w["dates"])


def test_ohlcv_to_wire_lengths_match():
    n = 5
    df = _make_df(n)
    w = _ohlcv_to_wire(df)
    assert len(w["dates"]) == n
    assert len(w["open"]) == n
    assert len(w["close"]) == n


# ---------------------------------------------------------------------------
# _build_execution_wire
# ---------------------------------------------------------------------------


def test_build_execution_wire_empty():
    w = _build_execution_wire(None, None, None, None)
    assert w == {}


def test_build_execution_wire_execution_only():
    w = _build_execution_wire(Execution(signal_frequency="hourly"), None, None, None)
    assert w["signal_frequency"] == "hourly"
    assert "slippage_bps" not in w


def test_build_execution_wire_costs_only():
    w = _build_execution_wire(None, Costs(slippage_bps=5.0), None, None)
    assert w["slippage_bps"] == 5.0
    assert "signal_frequency" not in w


def test_build_execution_wire_all():
    w = _build_execution_wire(
        Execution(signal_frequency="daily"),
        Costs(slippage_bps=2.5, fee_pct=0.001),
        Risk(stop="trailing_atr", value=2.5, atr_period=14),
        Sizing(weight=0.5, vol_target=0.15, leverage_limit=2.0),
    )
    assert w["signal_frequency"] == "daily"
    assert w["slippage_bps"] == 2.5
    assert w["fee_pct"] == 0.001
    assert w["stop_type"] == "trailing_atr"
    assert w["stop_value"] == 2.5
    assert w["stop_atr_period"] == 14
    assert w["position_weight"] == 0.5
    assert w["vol_target"] == 0.15
    assert w["leverage_limit"] == 2.0


# ---------------------------------------------------------------------------
# Client.validate_strategy
# ---------------------------------------------------------------------------


def test_validate_strategy_posts_to_correct_path():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, {"is_valid": True})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.validate_strategy(Strategy.rsi_threshold_long())
    url = mock_http.post.call_args[0][0]
    assert url.endswith("/api/validate-strategy")


def test_validate_strategy_sends_strategy_wire():
    c = Client(api_key="key")
    strat = Strategy.rsi_threshold_long()
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, {"is_valid": True})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.validate_strategy(strat)
    body = json.loads(mock_http.post.call_args[1]["content"])
    assert "condition_tree" in body
    assert "indicators" in body


def test_validate_strategy_returns_dict():
    c = Client(api_key="key")
    resp = {"is_valid": True, "errors": [], "warnings": []}
    mock_ctx, _, _ = _mock_http_context("POST", 200, resp)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.validate_strategy(Strategy.rsi_threshold_long())
    assert result["is_valid"] is True


def test_validate_strategy_propagates_error():
    c = Client(api_key="key")
    mock_ctx, _, _ = _mock_http_context("POST", 422, {"detail": "Invalid indicator ref."})
    patcher = patch("backtest360.client.httpx.Client", return_value=mock_ctx)
    with patcher, pytest.raises(Backtest360Error) as exc_info:
        c.validate_strategy(Strategy.rsi_threshold_long())
    assert exc_info.value.status == 422


# ---------------------------------------------------------------------------
# Client.latest_signal
# ---------------------------------------------------------------------------


def test_latest_signal_posts_to_correct_path():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, {"signal": 1})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.latest_signal(Strategy.rsi_threshold_long(), _make_df())
    url = mock_http.post.call_args[0][0]
    assert url.endswith("/api/latest-signal")


def test_latest_signal_body_has_strategy_and_data():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, {"signal": 0})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.latest_signal(Strategy.rsi_threshold_long(), _make_df())
    body = json.loads(mock_http.post.call_args[1]["content"])
    assert "strategy" in body
    assert "data_source" in body
    assert "ohlcv" in body["data_source"]


def test_latest_signal_returns_dict():
    c = Client(api_key="key")
    resp = {"signal": 1, "long_entry_fired": True, "long_exit_fired": False}
    mock_ctx, _, _ = _mock_http_context("POST", 200, resp)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.latest_signal(Strategy.rsi_threshold_long(), _make_df())
    assert result["signal"] == 1
    assert result["long_entry_fired"] is True


# ---------------------------------------------------------------------------
# Client.backtest_raw
# ---------------------------------------------------------------------------


def test_backtest_raw_sends_payload_unchanged():
    c = Client(api_key="key")
    payload = {"strategy": {"condition_tree": None, "indicators": []},
               "data_source": {"ohlcv": {}}}
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, {"status": "success"})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.backtest_raw(payload)
    sent = json.loads(mock_http.post.call_args[1]["content"])
    assert sent == payload


def test_backtest_raw_returns_full_response():
    c = Client(api_key="key")
    resp = {"status": "success", "result": {"stats": {"Sharpe": 1.5}}}
    mock_ctx, _, _ = _mock_http_context("POST", 200, resp)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.backtest_raw({})
    assert result == resp


def test_backtest_raw_posts_to_api_backtest():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, {})
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.backtest_raw({"x": 1})
    url = mock_http.post.call_args[0][0]
    assert url.endswith("/api/backtest")


# ---------------------------------------------------------------------------
# Client.backtest
# ---------------------------------------------------------------------------


def _backtest_response(sharpe=1.42):
    return {
        "status": "success",
        "result": {
            "stats": {"Sharpe": sharpe},
            "series": {
                "dates": ["2020-01-02", "2020-01-03"],
                "equity": [1.0, 1.01],
                "returns": [0.0, 0.01],
                "signals": [0, 1],
            },
            "trades": [],
        },
    }


def test_backtest_returns_result():
    c = Client(api_key="key")
    mock_ctx, _, _ = _mock_http_context("POST", 200, _backtest_response())
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.backtest(Strategy.rsi_threshold_long(), _make_df())
    assert isinstance(result, Result)
    assert result.stats["Sharpe"] == 1.42


def test_backtest_posts_strategy_and_data():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, _backtest_response())
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.backtest(Strategy.rsi_threshold_long(), _make_df())
    body = json.loads(mock_http.post.call_args[1]["content"])
    assert "strategy" in body
    assert "data_source" in body


def test_backtest_with_execution_and_costs():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, _backtest_response())
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.backtest(
            Strategy.rsi_threshold_long(), _make_df(),
            execution=Execution(signal_frequency="daily"),
            costs=Costs(slippage_bps=5.0),
        )
    body = json.loads(mock_http.post.call_args[1]["content"])
    assert body["execution"]["signal_frequency"] == "daily"
    assert body["execution"]["slippage_bps"] == 5.0


def test_backtest_with_benchmark():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, _backtest_response())
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.backtest(Strategy.rsi_threshold_long(), _make_df(), benchmark=_make_df())
    body = json.loads(mock_http.post.call_args[1]["content"])
    assert "benchmark" in body
    assert "ohlcv" in body["benchmark"]


def test_backtest_no_benchmark_omits_field():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, _backtest_response())
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.backtest(Strategy.rsi_threshold_long(), _make_df())
    body = json.loads(mock_http.post.call_args[1]["content"])
    assert "benchmark" not in body


def test_backtest_no_execution_omits_field():
    c = Client(api_key="key")
    mock_ctx, mock_http, _ = _mock_http_context("POST", 200, _backtest_response())
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        c.backtest(Strategy.rsi_threshold_long(), _make_df())
    body = json.loads(mock_http.post.call_args[1]["content"])
    assert "execution" not in body


def test_backtest_propagates_error():
    c = Client(api_key="key")
    mock_ctx, _, _ = _mock_http_context("POST", 422, {"detail": "Bad strategy."})
    patcher = patch("backtest360.client.httpx.Client", return_value=mock_ctx)
    with patcher, pytest.raises(Backtest360Error) as exc_info:
        c.backtest(Strategy.rsi_threshold_long(), _make_df())
    assert exc_info.value.status == 422


def test_backtest_unwraps_result_key():
    c = Client(api_key="key")
    # Engine wraps in {"result": {...}} — backtest() should unwrap it
    resp = {"status": "success", "result": {"stats": {"Sharpe": 2.0}, "series": {}, "trades": []}}
    mock_ctx, _, _ = _mock_http_context("POST", 200, resp)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        result = c.backtest(Strategy.rsi_threshold_long(), _make_df())
    assert result.stats["Sharpe"] == 2.0
