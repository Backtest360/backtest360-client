"""Tests for Backtest360Error and Client.__init__ / Client._request."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from backtest360.client import Backtest360Error, Client


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
    with pytest.raises(Exception):
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
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        with pytest.raises(Backtest360Error) as exc_info:
            c._request("GET", "/version")
    assert exc_info.value.status == 401
    assert exc_info.value.body == body


def test_request_429_raises_with_status_and_body():
    c = Client(api_key="key")
    body = {"detail": {"message": "Rate limit exceeded.", "code": "RATE_LIMITED"}}
    mock_ctx, _, _ = _mock_http_context("GET", 429, body)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        with pytest.raises(Backtest360Error) as exc_info:
            c._request("GET", "/api/backtest")
    assert exc_info.value.status == 429
    assert exc_info.value.body == body


def test_request_500_raises():
    c = Client(api_key="key")
    body = {"detail": "Internal server error."}
    mock_ctx, _, _ = _mock_http_context("GET", 500, body)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        with pytest.raises(Backtest360Error) as exc_info:
            c._request("GET", "/api/backtest")
    assert exc_info.value.status == 500


def test_request_non_json_body_stored_as_string():
    c = Client(api_key="key")
    mock_ctx, _, _ = _mock_http_context("GET", 502, text="<html>Bad Gateway</html>")
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        with pytest.raises(Backtest360Error) as exc_info:
            c._request("GET", "/version")
    assert exc_info.value.status == 502
    assert exc_info.value.body == "<html>Bad Gateway</html>"


def test_request_propagates_request_id_header():
    c = Client(api_key="key")
    body = {"detail": "Not found."}
    headers = {"x-request-id": "req-abc-999"}
    mock_ctx, _, _ = _mock_http_context("GET", 404, body, headers=headers)
    with patch("backtest360.client.httpx.Client", return_value=mock_ctx):
        with pytest.raises(Backtest360Error) as exc_info:
            c._request("GET", "/api/whatever")
    assert exc_info.value.request_id == "req-abc-999"


def test_client_importable_from_package():
    from backtest360 import Client as C  # noqa: F401

    assert C is Client
