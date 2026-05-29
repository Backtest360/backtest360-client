# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-05-29

### Added

- `MarketHours` dataclass — daily anchor-hour config for sub-daily execution
  (`open_hour`, `close_hour`, `strict_anchors`). Optional kwarg on `backtest()`
  and `latest_signal()`.
- `Settings` dataclass — engine-level run settings (`risk_free_rate`,
  `random_seed`, `on_bad_data`). Optional kwarg on `backtest()` and
  `latest_signal()`.
- `Client.backtest_signals(signals, ohlcv, ...)` — run a backtest from a
  pre-computed `pd.Series` of `{-1, 0, 1}` signals. Accepts the same
  execution-knob kwargs as `backtest()`.

### Breaking

- `Execution.fill` renamed to `Execution.entry_fill` and `Execution.exit_fill`
  (two independent fields). The engine always accepted them independently; the
  single `fill` field hid that degree of freedom. Update any code passing
  `Execution(fill=...)` to `Execution(entry_fill=..., exit_fill=...)`.
- `Risk.stop` vocab now matches the engine exactly: `"fixed"`, `"trailing"`,
  `"atr"`, `"trailing_atr"`. Previous values `"fixed_pct"`, `"trailing_pct"`,
  `"fixed_atr"` were never accepted by the engine and have been removed.
- `Risk.reentry` changed from `bool` to `str`. Valid values:
  `"immediate"` (default), `"next_signal"`, `"cooldown"`. The previous
  `bool` was never valid on the wire and would 422 whenever a stop was set.
- `Sizing.leverage_limit` default changed from `1.0` to `None` (no cap). The
  old default silently capped positions to ≤1.0× leverage.

---

## [0.1.1] — 2026-05-28

### Fixed

- Re-release of v0.1.0 under a new version number (PyPI does not allow filename reuse after deletion).

---

## [0.1.0] — 2026-05-28

First stable release. `pip install backtest360-client` now works without `--pre`.
Combines all alpha changes: env routing, access-surface guards, full docstrings,
and comprehensive test coverage.

---

## [0.1.0a3] — 2026-05-28

### Improved

- Comprehensive docstrings across the full public surface (`Client`, `Strategy`, `Execution`, `Costs`, `Risk`, `Sizing`, `Result`, all template classmethods) — `Args`, `Returns`, `Raises`, and `Example` blocks on every public method. Required for `mkdocstrings` SDK reference auto-generation in the docs site.

---

## [0.1.0a2] — 2026-05-28

### Breaking

- Key prefix changed from `bk_live_` to `b360_`. All previously issued keys are invalid — obtain a new key from [backtest360.com/dashboard](https://backtest360.com/dashboard).
- `Client.version()` now calls `GET /api/version` instead of `GET /version`.

### Added

- `BACKTEST360_ENGINE_URL` environment variable: sets the engine base URL when no `base_url` kwarg is passed. Prod default (`https://api.backtest360.com`) is used when neither is set.
- `BACKTEST360_API_KEY` environment variable: `Client()` with no kwargs now works when this variable is set (e.g. under Doppler). Missing both raises `Backtest360Error(code="SDK_NO_API_KEY")`.
- `Backtest360Error.code`: machine-readable error code string (e.g. `SDK_NO_API_KEY`, `SDK_PATH_FORBIDDEN`).
- `Client._request` path guard: raises `Backtest360Error(code="SDK_PATH_FORBIDDEN")` if `path` does not start with `/api/`. Prevents SDK from accidentally reaching admin routes.
- Public-surface lock test: asserts `Client` exposes exactly the seven documented public methods.

---

## [0.1.0a1] — 2026-05-27

First public release of the rewritten SDK. Prior internal alphas have been
removed from the repository history and from PyPI (see the clean-slate
migration in the repository README). This is a ground-up rewrite — there is
no migration path from the internal alpha versions.

### Added

- `Client` — synchronous HTTP wrapper over the public Backtest360 API.
  Methods: `backtest`, `backtest_raw`, `latest_signal`, `validate_strategy`,
  `list_strategies`, `list_indicators`, `version`.
- `Strategy` — strategy builder. Accepts boolean expression strings
  (`long_entry`, `long_exit`, `short_entry`, `short_exit`) and a list of
  indicator descriptors (`Strategy.indicator(...)`). Classmethods for
  pre-built templates: `rsi_threshold_long`, `rsi_mean_reversion`,
  `ma_crossover`, `momentum_6m_long`.
- `Execution` — execution timing dataclass (`entry`, `exit`,
  `signal_frequency`, `entry_window`, `exit_window`, `fill`).
- `Costs` — transaction costs dataclass (`slippage_bps`, `fee_pct`,
  `vol_scaled_slippage`, `vol_slippage_lookback`).
- `Risk` — stop-loss and drawdown protection dataclass (`stop`, `value`,
  `atr_period`, `reentry`, `cooldown_bars`, `max_drawdown`).
- `Sizing` — position sizing dataclass (`weight`, `vol_target`,
  `vol_target_lookback`, `leverage_limit`).
- `Result` — response wrapper. Properties: `stats` (dict), `trades` (list),
  `equity` / `returns` / `signals` (`pd.Series`), `raw` (full dict).
- `Backtest360Error` — single exception with `status`, `body`, `request_id`.
  Branch on `e.status` for fine-grained error handling.
- `py.typed` marker — first-class mypy / pyright support.
- MIT license.
- Full test suite (103 unit tests, no live network required).

### Notes

- Requires Python ≥ 3.9. Runtime dependencies: `httpx`, `pandas`.
- Alpha (`aN`) versioning: the public API surface may move between minor
  releases until `1.0.0`. Deprecated APIs will emit `DeprecationWarning` for
  at least one minor release before removal.
- If PyPI refused to re-upload the `0.1.0a1` wheel (filename burned by a
  previous artifact), this release would have been tagged `0.1.0a2` — check
  the git tag for the canonical version number.
