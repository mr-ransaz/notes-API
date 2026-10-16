# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Windows live HTTP smoke script with isolated Uvicorn, an environment secret,
  temporary SQLite, current-source imports, and process-tree cleanup.
- CI configuration for both pytest entry points and a separate Docker build-only
  job. Hosted CI and Docker execution remain unverified.

### Fixed

- PowerShell curl form login no longer includes the pipeline's appended line
  ending in the submitted password. All 19 curl commands were verified over
  real HTTP in Windows PowerShell 5.1 and PowerShell 7.6.5 with a supplied test
  password prompt.
- Health OpenAPI response now describes the required status value "ok" while
  preserving the existing response body and status code.
- Placeholder scan no longer matches its own documented regex and examples.
- Fresh checkouts create the private pytest temporary parent before pytest's
  basetemp setup. Smoke temporary-directory creation is also recursive and
  idempotent, requesting mode 0o700.

### Verified locally on 2026-10-17

- 117 tests pass through both pytest entry points, with 100.00% application
  statement/branch coverage. Live smoke, success/failure cleanup, and isolated
  reload startup passed on Windows / Python 3.14.0.
- Reproduced the missing-parent failure (101 setup errors), then passed both
  entry points after deleting `.tmp` before each run. A fresh local clone with
  a new Python 3.14 venv passed installation, available gates and live smoke;
  the clone was deleted afterward. Hosted CI rerun and Docker remain unverified.

## 0.1.0 - 2026-10-16

### Added

- Case-insensitive registration, Argon2id password storage, OAuth2 password
  form login, HS256 access tokens, and current-user endpoint.
- Private notes CRUD, bounded pagination, and literal title/body search using
  bound SQL parameters. Foreign-owned notes return 404.
- Per-process, bounded, in-memory failed-login limiting with Retry-After.
- Strict JSON inputs, sanitized JSON errors, mandatory environment secret,
  and unauthenticated health endpoint.
- Isolated SQLite tests with a 90% branch-enabled coverage gate, ruff checks,
  a non-root Dockerfile, and a Python 3.14 GitHub Actions workflow.

Docker and hosted CI execution have not been verified locally.
