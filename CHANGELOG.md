# Changelog

All notable changes to this project are documented here.

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
