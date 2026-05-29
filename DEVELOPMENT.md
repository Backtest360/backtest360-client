# Development Guide — backtest360-client

How we work on this repo: branch discipline, release flow, and changelog style.

---

## Branch & worktree discipline

Every session that will make commits works in its own `git worktree` on its own branch. Sessions never share a working directory or a branch — they only meet on `main` after merging.

```bash
git worktree add ~/Code-client-<topic> -b backtest360-client/<topic>
cd ~/Code-client-<topic>
git branch --show-current   # sanity-check
```

Rules:
- One topic per branch. Never mix unrelated changes.
- Merge via squash PR. Delete the branch and worktree after merge.
- Never commit directly to `main` except for trivial one-line doc fixes.
- Start of session: run `git worktree list` and flag any open worktrees from a previous session.
- End of session: all five steps done — PR merged, local branch deleted, worktree removed, local main fast-forwarded, `git worktree list` shows only `main`.

---

## Release flow

Releases are driven by git tags. CI does everything else.

```bash
# 1. Merge the PR to main
# 2. Pull main locally
git pull --ff-only origin main

# 3. Tag
git tag vX.Y.Z
git push origin vX.Y.Z
```

On tag push, the `release` CI workflow:
1. Runs the full test suite
2. Builds the wheel and sdist
3. Publishes to PyPI via OIDC trusted publishing (no token stored)
4. Creates a GitHub Release

**Version numbering** — `MAJOR.MINOR.PATCH`, semver. Pre-1.0: breaking changes bump `MINOR`. Post-1.0: breaking changes bump `MAJOR`. Pre-release suffixes: `aN` (alpha), `bN` (beta), `rcN` (release candidate) — require `pip install --pre` to install.

**PyPI is permanent.** A version number published to PyPI cannot be re-uploaded. Get the version right before tagging.

---

## Changelog style

Every release gets an entry in `CHANGELOG.md` under `## [X.Y.Z] — YYYY-MM-DD`.

**Sections used:** `Added`, `Changed`, `Fixed`, `Breaking`, `Removed`.

**Tone:** Neutral and forward-looking. Describe what changed, not what was wrong before. Avoid language that implies the previous release was defective — users who hit a bug already know; public changelogs are read by prospective users too.

Prefer:
> `Risk.stop` vocab updated to match the engine: `"fixed"`, `"trailing"`, `"atr"`, `"trailing_atr"`. Previous values removed.

Avoid:
> Previous values were never accepted by the engine and have been removed.

**Breaking changes** must state: what changed, what the new value/type/default is, and what callers need to update. One bullet per breaking item, no hedging.
