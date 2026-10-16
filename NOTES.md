# Decisions and verification notes

## Environment and dependencies

- Windows PowerShell, Python 3.14.0, local `.venv`.
- The empty repository had no source files or existing commits to preserve.
- Venv's initial ensurepip failed with the host temporary directory. Retrying
  ensurepip with `TEMP`/`TMP` pointing to ignored project-local `.tmp` succeeded.
  All subsequent pip commands use project-local temporary storage and no cache.
- Requested packages installed successfully on CPython 3.14.0 / Windows amd64:
  FastAPI 0.143.3, Uvicorn 0.54.0, SQLAlchemy 2.1.4, Pydantic 2.14.1,
  pydantic-settings 2.16.0, argon2-cffi 25.1.0, PyJWT 2.15.1,
  pytest 9.1.1, pytest-cov 7.1.0, httpx 0.28.1, ruff 0.17.1.
  pip selected CPython 3.14 wheels for SQLAlchemy, pydantic-core, coverage,
  and cffi; argon2-cffi-bindings used a compatible abi3 wheel.
- python-multipart 0.0.32 is required by FastAPI's OAuth2 form parser.
  It also installed successfully. Direct dependencies are pinned to versions
  actually installed; transitive dependencies are not fully locked.
- Compatibility constraint: FastAPI initially resolved Starlette 1.8.0, whose
  TestClient emits a deprecation warning for the requested httpx backend and
  requests httpx2. With warnings treated as errors, test collection failed.
  Starlette 0.52.1 installed successfully on Python 3.14, satisfies FastAPI's
  requirements (`pip check` passed), and retains httpx TestClient support.
  It is pinned explicitly rather than replacing httpx or suppressing warnings.
  AnyIO 4.15.1 also deprecated the `anyio.abc.BlockingPortal` alias used by that
  Starlette TestClient. AnyIO 4.11.0 is pinned for that compatibility boundary;
  its Python 3.14 install and `pip check` succeeded.
- setuptools 84.0.0 installed successfully; editable package build succeeded
  with `pip install --no-cache-dir --no-build-isolation -e '.[dev]'`.
- No requested library needed an alternative. Linux/container compatibility
  remains unverified until Docker or hosted CI runs.

## Design

- App factory; settings are validated during lifespan startup, not module import.
  No default secret. Minimum 32 non-padding characters; example placeholder is
  rejected. Secrets use Pydantic SecretStr.
- File-based SQLite; startup calls `metadata.create_all` through `init_db`.
  Foreign keys are enabled on each connection. No migration system.
- Usernames are stored lowercase and protected by a SQLite NOCASE unique
  constraint, including concurrent registration conflicts.
- Argon2id library defaults; a fresh dummy hash is made once at startup for
  unknown-user verification. Tokens require sub/exp/iat and HS256 explicitly.
- Basic error handlers are included in stage 1 so password validation cannot
  echo submitted values. Error hardening is completed and tested in stage 3.
- Reference patterns checked against the official
  [FastAPI OAuth2/JWT documentation](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
  and [SQLAlchemy SQLite documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html).

## Manual checks

- Docker executable is not installed / not on PATH; build and run unverified.
- Browser `/docs` walkthrough, GitHub repository creation, first push, and hosted
  CI execution are left to the owner. No push or tags are created locally.

## Stage 1 results

- Auth/config/database scaffold complete; 53 tests passed with 100.00% combined
  statement and branch coverage on Windows / Python 3.14.0.
- Ordered gates: ruff check passed; ruff format --check passed; pytest passed;
  git diff --check passed. Docker unavailable, so build skipped explicitly.
- No login rate limiting yet; it is scheduled for stage 3.
