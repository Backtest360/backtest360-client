# Versioning

`backtest360-client` follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — breaking changes to the public surface (class names, method signatures, response shapes)
- **MINOR** — additive changes: new methods, new optional args, new templates
- **PATCH** — bug fixes, internal-only changes, doc fixes

**Pre-1.0 (`0.x.y`):** the API surface may move between minor versions. README says so
explicitly. Deprecated APIs emit `DeprecationWarning` for at least one minor release before removal.

**Pre-release suffixes:** `aN` (alpha — rough), `bN` (beta — feature-complete),
`rcN` (frozen, bug-fix only), then the unsuffixed stable.

**Current release:** see [CHANGELOG](https://github.com/Backtest360/backtest360-client/blob/main/CHANGELOG.md).
