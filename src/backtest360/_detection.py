"""Bar-frequency and market-hours detection helpers.

Copied (not imported) from the engine so the SDK has zero engine dependency.
These are private to the SDK — do not import from user code.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Bar-frequency table (kept minimal — only the fields needed for detection)
# ---------------------------------------------------------------------------

_BAR_FREQUENCIES = {
    "daily":   {"bars_per_day": 1,        "label": "daily"},
    "4h":      {"bars_per_day": 6,        "label": "4h"},
    "hourly":  {"bars_per_day": 24,       "label": "hourly"},
    "30min":   {"bars_per_day": 48,       "label": "30min"},
    "15min":   {"bars_per_day": 96,       "label": "15min"},
    "5min":    {"bars_per_day": 288,      "label": "5min"},
    "1min":    {"bars_per_day": 1440,     "label": "1min"},
    "weekly":  {"bars_per_day": 1.0 / 7,  "label": "weekly",  "bars_per_year": 52},
    "monthly": {"bars_per_day": 1.0 / 30, "label": "monthly", "bars_per_year": 12},
}


def detect_bar_frequency(index: pd.DatetimeIndex) -> dict:
    """Detect bar frequency from a DatetimeIndex.

    Returns a dict with at least 'label' and 'bars_per_day'.
    """
    if len(index) < 2:
        return dict(_BAR_FREQUENCIES["daily"])

    diffs = index[1:] - index[:-1]
    median_hours = float(np.median([d.total_seconds() / 3600 for d in diffs]))

    if median_hours >= 400:
        return dict(_BAR_FREQUENCIES["monthly"])
    if median_hours >= 60:
        return dict(_BAR_FREQUENCIES["weekly"])
    if median_hours >= 20:
        return dict(_BAR_FREQUENCIES["daily"])
    if median_hours >= 3:
        return dict(_BAR_FREQUENCIES["4h"])
    if median_hours >= 0.8:
        return dict(_BAR_FREQUENCIES["hourly"])
    if median_hours >= 0.4:
        return dict(_BAR_FREQUENCIES["30min"])
    if median_hours >= 0.17:
        return dict(_BAR_FREQUENCIES["15min"])
    if median_hours >= 0.05:
        return dict(_BAR_FREQUENCIES["5min"])
    return dict(_BAR_FREQUENCIES["1min"])


# ---------------------------------------------------------------------------
# Market-hours detection
# ---------------------------------------------------------------------------

def detect_market_hours(df: pd.DataFrame) -> dict:
    """Detect 24h vs session and open/close hours from OHLCV data.

    Returns dict with: is_24h, detected_open_hour, detected_close_hour, confidence.
    """
    if len(df) < 2:
        return {"is_24h": True, "confidence": "low",
                "detected_open_hour": 0.0, "detected_close_hour": 0.0}

    ts = df.index.to_series()
    all_diffs = ts.diff().dropna()
    median_spacing = all_diffs.median()
    median_hours = median_spacing.total_seconds() / 3600
    sample_days = int((df.index[-1] - df.index[0]).total_seconds() / 86400)
    confidence = "high" if sample_days >= 21 else "low"

    if median_hours >= 23:
        return _detect_from_daily_bars(df, confidence, sample_days)

    return _detect_from_subbar(df, all_diffs, median_spacing, confidence, sample_days, median_hours)


def _detect_from_daily_bars(df: pd.DataFrame, confidence: str, sample_days: int) -> dict:
    if hasattr(df.index[0], "dayofweek"):
        weekday_counts = df.index.dayofweek.value_counts()
        has_weekend = 5 in weekday_counts.index or 6 in weekday_counts.index
        if not has_weekend and sample_days >= 14:
            return {"is_24h": False, "confidence": confidence,
                    "detected_open_hour": 9.5, "detected_close_hour": 16.0}
    return {"is_24h": True, "confidence": confidence,
            "detected_open_hour": 0.0, "detected_close_hour": 0.0}


def _detect_from_subbar(
    df: pd.DataFrame, all_diffs: pd.Series,
    median_spacing: pd.Timedelta, confidence: str, sample_days: int,
    median_hours: float,
) -> dict:
    gap_threshold = median_spacing * 3
    large_gaps = all_diffs[all_diffs > gap_threshold]

    if len(large_gaps) < 3:
        return {"is_24h": True, "confidence": confidence,
                "detected_open_hour": 0.0, "detected_close_hour": 0.0}

    df_index = df.index
    idx_position = {ts: i for i, ts in enumerate(df_index)}
    close_hours: list = []
    open_hours: list = []

    for gap_ts in large_gaps.index:
        pos = idx_position.get(gap_ts)
        if pos is not None and pos > 0:
            prev_bar = df_index[pos - 1]
            if hasattr(prev_bar, "hour"):
                close_hours.append(prev_bar.hour + prev_bar.minute / 60)
            if hasattr(gap_ts, "hour"):
                open_hours.append(gap_ts.hour + gap_ts.minute / 60)

    if not close_hours or not open_hours:
        return {"is_24h": True, "confidence": confidence,
                "detected_open_hour": 0.0, "detected_close_hour": 0.0}

    close_mode = Counter(close_hours).most_common(1)[0]
    open_mode = Counter(open_hours).most_common(1)[0]
    close_consistency = close_mode[1] / len(close_hours)
    open_consistency = open_mode[1] / len(open_hours)

    if close_consistency > 0.6 and open_consistency > 0.6:
        detected_close = close_mode[0] + median_hours
        return {"is_24h": False, "confidence": confidence,
                "detected_open_hour": open_mode[0], "detected_close_hour": detected_close}

    return {"is_24h": True, "confidence": confidence,
            "detected_open_hour": 0.0, "detected_close_hour": 0.0}


# ---------------------------------------------------------------------------
# Trading-days-per-year detection
# ---------------------------------------------------------------------------

def detect_trading_days_per_year(ohlcv: pd.DataFrame, is_24h: bool) -> Optional[int]:
    """Auto-detect trading days per year from data density."""
    if is_24h:
        return 365

    dates = ohlcv.index.normalize().unique()
    if len(dates) < 2:
        return None

    span_days = (dates[-1] - dates[0]).days
    if span_days < 60:
        return None

    trading_days_ratio = len(dates) / span_days
    estimated = int(trading_days_ratio * 365)

    if estimated < 200 or estimated > 270:
        return None

    return estimated


# ---------------------------------------------------------------------------
# Data-quality assessment
# ---------------------------------------------------------------------------

def assess_data_quality(
    ohlcv: pd.DataFrame,
    bar_frequency: str,
    is_24h: bool,
    session_open: float,
    session_close: float,
) -> tuple:
    """Return (missing_bars, bad_prices, warnings)."""
    warnings_list: list = []

    price_cols = [c for c in ["open", "high", "low", "close"] if c in ohlcv.columns]
    bad_prices = 0
    for col in price_cols:
        zeros = int((ohlcv[col] == 0).sum())
        negatives = int((ohlcv[col] < 0).sum())
        nans = int(ohlcv[col].isna().sum())
        bad_prices += zeros + negatives + nans

    if bad_prices > 0:
        warnings_list.append(f"{bad_prices} bad price values (zero/negative/NaN)")

    if len(ohlcv) < 2:
        return 0, bad_prices, warnings_list

    if bar_frequency == "daily":
        missing_bars = _count_missing_daily(ohlcv, is_24h)
    else:
        missing_bars = _count_missing_intraday(ohlcv, is_24h, session_open, session_close)

    if missing_bars > 0:
        warnings_list.append(f"{missing_bars} missing bars")

    return missing_bars, bad_prices, warnings_list


def _count_missing_daily(ohlcv: pd.DataFrame, is_24h: bool) -> int:
    dates = ohlcv.index.normalize().unique().sort_values()
    missing = 0
    for i in range(1, len(dates)):
        gap_days = (dates[i] - dates[i - 1]).days
        if is_24h:
            if gap_days > 1:
                missing += gap_days - 1
        else:
            weekday = dates[i - 1].weekday()
            expected_gap = 3 if weekday == 4 else (2 if weekday == 5 else 1)
            if gap_days > expected_gap:
                missing += gap_days - expected_gap
    return missing


def _count_missing_intraday(
    ohlcv: pd.DataFrame, is_24h: bool,
    session_open: float, session_close: float,
) -> int:
    diffs = ohlcv.index[1:] - ohlcv.index[:-1]
    median_spacing = pd.Series(diffs).median()
    threshold = median_spacing * 1.5
    missing = 0

    if is_24h:
        for d in diffs:
            if d > threshold:
                missed = int(d / median_spacing) - 1
                missing += max(0, missed)
        return missing

    for i, d in enumerate(diffs):
        if d <= threshold:
            continue
        ts = ohlcv.index[i]
        next_ts = ohlcv.index[i + 1]
        is_overnight = ts.normalize() != next_ts.normalize()
        is_weekend = ts.weekday() == 4 and next_ts.weekday() == 0
        if is_overnight or is_weekend:
            if is_weekend:
                expected_hours = (24 - session_close + session_open) + 48
            else:
                expected_hours = 24 - session_close + session_open
            expected_gap = pd.Timedelta(hours=expected_hours)
            if d > expected_gap * 1.5:
                missed = int(d / pd.Timedelta(hours=24)) - 1
                missing += max(0, missed)
        else:
            missed = int(d / median_spacing) - 1
            missing += max(0, missed)

    return missing
