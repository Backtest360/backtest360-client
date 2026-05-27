"""Tests for Backtest360Error."""

import pytest

from backtest360.client import Backtest360Error


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
