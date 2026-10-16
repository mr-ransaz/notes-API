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
- A live Uvicorn HTTP session and the README curl commands were not exercised.
  Tests request `/docs` and validate its OAuth2 OpenAPI configuration using
  TestClient; this does not verify browser Authorize behavior.

## Stage 1 results

- Auth/config/database scaffold complete; 53 tests passed with 100.00% combined
  statement and branch coverage on Windows / Python 3.14.0.
- Ordered gates: ruff check passed; ruff format --check passed; pytest passed;
  git diff --check passed. Docker unavailable, so build skipped explicitly.
- No login rate limiting yet; it is scheduled for stage 3.

## Stage 2 results

- Added notes CRUD. Every note lookup filters on both ID and authenticated
  owner ID; foreign notes and absent notes return the same 404 response.
- Indexed `owner_id`; list results are ordered by ascending ID before applying
  limit/offset. Default limit 20, maximum 100, offset bounded to SQLite's signed
  64-bit integer range. No total count is returned.
- Search uses SQLAlchemy bound parameters and `icontains(..., autoescape=True)`
  on title/body; `%`, `_`, and the escape character are literal. SQLite's default
  case folding is ASCII-oriented. Search input is limited to 200 characters.
- Create requires a nonblank title; body defaults to empty. PATCH requires at
  least one field; explicit null and unknown fields are rejected. Empty body is
  allowed. Character limits are 200 / 10000, not byte limits.
- Ordered gates passed: ruff check, ruff format --check, pytest (98 tests,
  100.00% statement and branch coverage), git diff --check. Docker unavailable.

## Stage 3 results

- Added a bounded, per-process login limiter: five failures per normalized
  username + transport IP in a fixed 300-second window. The sixth request is
  blocked with 429 and Retry-After; even correct credentials stay blocked until
  expiry. A successful login before blocking clears the counter.
- A single lock covers checking, credential verification, and recording the
  result. Concurrent attempts cannot bypass accounting, at the cost of serial
  login verification. State is capped at 10000 failed-login keys. Expired keys
  are removed on the next attempt; new keys fail closed if the cap is reached.
  Cleanup is O(k) time and space for k tracked keys (bounded at 10000), in
  addition to database lookup and Argon2 verification. No throughput benchmark
  or production-grade abuse protection is claimed.
- The limiter resets with each app lifespan/process. It does not share state
  between workers, trust forwarded IP headers, or rate-limit registration.
  README documents these limitations and saturation behavior.
- Login form rejects unknown/repeated fields. JSON error responses omit input
  values and exception contexts. Configuration error strings also hide inputs.
  OpenAPI includes the actual error envelope and omits null from PATCH fields.
- JWT subjects are bounded to SQLite's positive signed 64-bit ID range;
  boundary tests cover both valid maximum and out-of-range subjects.
- Dockerfile uses Python 3.14 slim, UID 10001, explicit user/group, `/data`
  volume storage, and runtime environment configuration. No secret is copied.
  Docker unavailable on PATH: neither build nor run was performed.
- CI targets ubuntu-latest / Python 3.14 with read-only repository permission,
  checkout@v6, setup-python@v6, and install/lint/format/coverage steps. Action
  references were checked against the official
  [checkout](https://github.com/actions/checkout) and
  [setup-python](https://github.com/actions/setup-python/blob/main/docs/advanced-usage.md)
  documentation. Hosted execution remains unverified.
- README includes PowerShell and Docker startup, configuration/endpoint tables,
  stdin-based curl examples, security behavior, and known limitations.
- No implementation outside the requested stack. Compatibility pins for
  Starlette/AnyIO are the only additional runtime constraints; python-multipart
  is necessary for OAuth2 forms. Build backend is pinned to tested setuptools
  84.0.0. Direct runtime/dev dependencies are pinned; transitives are not locked.

### Final local verification (Windows / Python 3.14.0)

- Ordered gates passed: `ruff check .`, `ruff format --check .`,
  `.venv/Scripts/pytest.exe -q`, `git diff --check`. Docker gate skipped because
  no executable is available. Full executable commands are in README.
- `python -m pytest`: 113 passed; `pytest -q`: 113 passed, with `.venv/Scripts`
  first on the command's PATH. Both measured 100.00% combined statement/branch
  coverage: 324 statements and 38 branches, none missing. Required minimum: 90%.
- `python -m pip check`: no broken requirements found.
- `python -m pip install --no-cache-dir --no-build-isolation -e '.[dev]'`:
  editable package build/install succeeded with the final dependency pins.
- `python -m pip wheel --no-cache-dir --no-build-isolation --no-deps
  --wheel-dir .tmp/wheels .`: package wheel built successfully. This validates
  packaging on Windows, not Linux or Docker runtime behavior.
- `python -m uvicorn --version`: Uvicorn 0.54.0 / CPython 3.14.0 on Windows.
- No hosted CI success, Docker success, live browser success, or constant-time
  authentication timing is asserted. No push, remote creation, or tags.
