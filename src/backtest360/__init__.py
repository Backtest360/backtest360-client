"""Backtest360 Python client SDK."""

from importlib.metadata import PackageNotFoundError, version

from backtest360.client import Backtest360Error

try:
    __version__ = version("backtest360-client")
except PackageNotFoundError:
    __version__ = "0.0.0.dev"

__all__ = ["Backtest360Error", "__version__"]
