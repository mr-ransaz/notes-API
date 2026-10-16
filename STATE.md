# Project state

- Version: 0.1.0; temporary-parent fix verified locally on 2026-10-17.
- Last implementation commit: a97d6e3 (early private temporary-directory setup).
- Regression-test commit: 2d3d7dd (missing/existing roots and database isolation).
- Environment: Windows, Python 3.14.0. No dependency changes.
- Local commits only; no pushes, tags or external repository changes.

## Verified locally

- Removed `.tmp` before the fix: reproduced 13 passed / 101 setup errors.
- Conftest creates `.tmp` and `.tmp/pytest` before fixtures; smoke does the same
  recursive/idempotent root creation. All specify mode 0o700.
- Removed `.tmp` independently before module pytest and executable pytest:
  both passed 117 tests with 100.00% application branch-enabled coverage.
- Coverage: notes_api, 325 statements / 38 branches, none missing; minimum 90%.
  Separate subprocess smoke code is outside that coverage scope.
- Post-commit local gates: lint, format, both pytest entry points, whitespace
  check, placeholder scan and live README/smoke checks passed.
- Fresh local clone at 2d3d7dd had no `.tmp`; new venv created with py -3.14,
  `.[dev]` installed successfully and pip check passed (Python 3.14.0).
- Fresh-clone available gates passed, including 117 tests / 100.00% coverage
  through each entry point. Smoke also passed with `.tmp` removed again.
- Both copies passed all 19 curl commands in PowerShell 5.1 and 7.6.5 using
  real HTTP and a supplied test password prompt.
- Disposable sibling clone and venv deleted; independent absence check passed.
- Docker unavailable on PATH in both copies; no build/run performed.
- User-reported hosted CI failure reproduced locally; hosted rerun unverified.

## Manual checks still required

- Owner: publish the fix and rerun hosted Ubuntu CI; confirm its result.
- Linux execution/POSIX permissions, Docker build/run and volume persistence.
- Browser /docs Authorize walkthrough and human-entered hidden password prompt.
- Load testing, external security assessment and authentication timing unmeasured.
