"""Smoke test — verifies the package installs and imports cleanly."""


def test_import():
    import backtest360  # noqa: F401


def test_version_attribute_absent_before_dtos():
    """__init__.py is intentionally empty at this stage; no AttributeError."""
    import backtest360

    assert not hasattr(backtest360, "BacktestClient")
