"""Integration tests — live HTTP against a running engine.

Requires two environment variables:
  BACKTEST360_API_KEY   — a valid customer key for the target engine
  BACKTEST360_ENGINE_URL — engine base URL, e.g. http://178.105.18.196:8000
                           (defaults to https://api.backtest360.com)

Run with:
  BACKTEST360_API_KEY=<key> BACKTEST360_ENGINE_URL=http://178.105.18.196:8000 \
      pytest -q -m integration
"""

import os

import numpy as np
import pandas as pd
import pytest

from backtest360.client import BacktestClient
from backtest360.dtos import BacktestConfig, MarketData
from backtest360.strategies import rsi_threshold_long

_ENGINE_URL = os.environ.get("BACKTEST360_ENGINE_URL", "https://api.backtest360.com")
_API_KEY = os.environ.get("BACKTEST360_API_KEY", "")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> BacktestClient:
    if not _API_KEY:
        pytest.skip("BACKTEST360_API_KEY not set")
    return BacktestClient(api_key=_API_KEY, base_url=_ENGINE_URL)


@pytest.fixture(scope="module")
def sample_md() -> MarketData:
    idx = pd.date_range("2023-01-02", periods=365, freq="B", tz="UTC")
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, len(idx)))
    df = pd.DataFrame(
        {
            "open": close * (1 + rng.uniform(-0.002, 0.002, len(idx))),
            "high": close * (1 + rng.uniform(0.001, 0.005, len(idx))),
            "low": close * (1 - rng.uniform(0.001, 0.005, len(idx))),
            "close": close,
            "volume": rng.integers(500_000, 2_000_000, len(idx)).astype(float),
        },
        index=idx,
    )
    md = MarketData()
    md.load(df)
    return md


# ---------------------------------------------------------------------------
# /version
# ---------------------------------------------------------------------------


def test_version_returns_engine_field(client: BacktestClient) -> None:
    v = client.version()
    assert "engine" in v, f"Expected 'engine' in version response; got {v}"


def test_version_returns_min_client(client: BacktestClient) -> None:
    v = client.version()
    assert "min_client" in v
    assert isinstance(v["min_client"], str)


def test_version_returns_api_contract(client: BacktestClient) -> None:
    v = client.version()
    assert v.get("api_contract") == "1"


# ---------------------------------------------------------------------------
# /api/indicators
# ---------------------------------------------------------------------------


def test_list_indicators_returns_list(client: BacktestClient) -> None:
    indicators = client.list_indicators()
    assert isinstance(indicators, list)
    assert len(indicators) > 0, "Expected at least one indicator in registry"


def test_indicators_have_id_field(client: BacktestClient) -> None:
    indicators = client.list_indicators()
    for ind in indicators[:5]:
        assert "id" in ind, f"Indicator missing 'id': {ind}"


# ---------------------------------------------------------------------------
# /api/strategies
# ---------------------------------------------------------------------------


def test_list_strategies_returns_list(client: BacktestClient) -> None:
    strategies = client.list_strategies()
    assert isinstance(strategies, list)
    assert len(strategies) > 0, "Expected at least one strategy in catalog"


# ---------------------------------------------------------------------------
# /api/validate-strategy
# ---------------------------------------------------------------------------


def test_validate_strategy_rsi_threshold_long(client: BacktestClient) -> None:
    result = client.validate_strategy(rsi_threshold_long())
    assert result.valid, f"rsi_threshold_long validation failed: {result.issues}"


# ---------------------------------------------------------------------------
# /api/backtest
# ---------------------------------------------------------------------------


def test_backtest_returns_result(client: BacktestClient, sample_md: MarketData) -> None:
    result = client.backtest(rsi_threshold_long(), BacktestConfig(), sample_md)
    assert result is not None
    assert result.statistics is not None


def test_backtest_statistics_sharpe_is_float(client: BacktestClient, sample_md: MarketData) -> None:
    result = client.backtest(rsi_threshold_long(), BacktestConfig(), sample_md)
    sr = result.statistics.sharpe_ratio
    assert sr is None or isinstance(sr, (int, float)), (
        f"sharpe_ratio should be numeric or None; got {type(sr)}"
    )


def test_backtest_run_result_has_returns(client: BacktestClient, sample_md: MarketData) -> None:
    result = client.backtest(rsi_threshold_long(), BacktestConfig(), sample_md)
    assert result.run_result is not None
    assert len(result.run_result.returns) > 0
