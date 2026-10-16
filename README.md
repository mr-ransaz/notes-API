# notes-api

A small REST API for private personal notes, built as a backend/security student
portfolio project by **MR Ransaz**. Version **0.1.0**, MIT licensed, Python **3.14.x**.
Repository: [mr-ransaz/notes-api](https://github.com/mr-ransaz/notes-api).

FastAPI serves the API and Swagger UI; SQLAlchemy 2 uses SQLite; Pydantic v2
validates inputs and configuration. Authentication uses Argon2id and PyJWT.
Users can create, search, read, update, and delete their own notes.
This is a small demonstrator with explicit deployment limitations.

## Quick start: PowerShell

From this folder on Windows with Python 3.14 installed:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[dev]"
$env:NOTES_API_SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
$env:NOTES_API_DATABASE_URL = 'sqlite:///./notes.db'
.\.venv\Scripts\python.exe -m uvicorn notes_api.main:app --reload --no-proxy-headers
```

Open [Swagger UI](http://127.0.0.1:8000/docs). Register using `/auth/register`,
then click **Authorize** and enter the same username/password. Swagger submits
the OAuth2 form to `/auth/login` and sends the bearer token on protected calls.
Registration itself returns a user record, without a token.

The secret above lasts for the current PowerShell session. To keep a stable
development key, copy `.env.example` to `.env` and replace the placeholder with
output from this command:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

`.env` is ignored by Git and Docker. Environment variables take precedence over
`.env`. The example placeholder is deliberately rejected at startup. Changing
the signing secret invalidates existing tokens. Keep the real key private.
SQLite tables are created on startup; the database's parent directory must exist
and be writable. `create_all` creates missing tables but does not migrate schemas.

## Quick start: Docker

Docker must be installed and running. These commands are provided for a manual
check; the image has **not** been built or run in the development environment.

```powershell
docker build -t notes-api:0.1.0 .
$env:NOTES_API_SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
docker volume create notes-api-data
docker run --rm --name notes-api -p 127.0.0.1:8000:8000 --env NOTES_API_SECRET_KEY --env NOTES_API_DATABASE_URL=sqlite:////data/notes.db --mount source=notes-api-data,target=/data notes-api:0.1.0
```

The Dockerfile uses `python:3.14-slim`, runs as UID 10001, and stores SQLite in
`/data` on a volume. It installs runtime dependencies only and copies no secret.
The run command binds to localhost. A bind mount needs write permission for UID
10001; the named volume above avoids host-directory permission setup. Persist
the same secret between runs if existing tokens need to remain valid.

## Configuration

Settings are read at startup with the `NOTES_API_` prefix. Startup fails when the
secret is missing or invalid. CORS middleware is absent and has no enable switch.

| Variable | Default | Meaning |
| --- | --- | --- |
| `NOTES_API_SECRET_KEY` | Required; no default | HS256 key; at least 32 characters after trimming; generate randomly. The example placeholder is rejected. |
| `NOTES_API_DATABASE_URL` | `sqlite:///./notes.db` | File-based SQLite SQLAlchemy URL. Docker default: `sqlite:////data/notes.db`. Other backends and `:memory:` are rejected. |
| `NOTES_API_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token lifetime, integer from 1 to 1440 minutes. |

## Endpoints

All request/response bodies use JSON except the login request, which uses
`application/x-www-form-urlencoded`. Error responses use the shape below.

| Method | Path | Auth | Success / behavior |
| --- | --- | --- | --- |
| POST | `/auth/register` | No | 201, `{id, username}`; duplicate username: 409 |
| POST | `/auth/login` | No | 200, `{access_token, token_type}`; invalid credentials: 401; limited: 429 |
| GET | `/users/me` | Bearer | 200, `{id, username}` |
| POST | `/notes` | Bearer | 201, `{id, title, body}` |
| GET | `/notes` | Bearer | 200, array of owned notes, ascending ID |
| GET | `/notes/{id}` | Bearer | 200, note; absent or foreign-owned: 404 |
| PATCH | `/notes/{id}` | Bearer | 200, updated note; absent or foreign-owned: 404 |
| DELETE | `/notes/{id}` | Bearer | 204, empty body; absent or foreign-owned: 404 |
| GET | `/health` | No | 200, `{"status":"ok"}`; liveness only |

`GET /notes` accepts `limit` (default 20, 1–100), `offset` (default 0, nonnegative
SQLite signed 64-bit integer), and optional `q` (up to 200 characters). Search
matches literal substrings in title or body, with ASCII case-insensitive SQLite
matching. `%`, `_`, and `/` are treated literally. Empty `q` applies no filter.
Pagination follows filtering and returns an array without a total count.

Titles must contain a non-whitespace character and be 1–200 characters long;
bodies may be empty and are limited to 10000 characters. Create requires a title
and defaults the body to empty. PATCH must supply at least one field, leaves
omitted fields unchanged, and rejects explicit null. Unknown JSON fields and
unknown list-query parameters are rejected with 422. Unknown or repeated login
form fields are also rejected. The standard OAuth2 form fields are accepted;
scopes and client credentials are not used for authorization.

```json
{"error":{"code":"http_404","message":"Note not found","details":[]}}
```

Validation errors have `code: "validation_error"`, a general message, and details
with `location`, `type`, and `message`. Input values and exception contexts are
omitted. Unexpected server errors return a generic 500 JSON response.

## curl examples: PowerShell

Use `curl.exe` explicitly because Windows PowerShell may alias `curl` to
`Invoke-WebRequest`. JSON is sent through stdin to avoid native argument quoting
problems. UTF-8 stdin is selected explicitly for Windows PowerShell 5.1 as well
as PowerShell 7. The login body URI-encodes the entered password before sending it.
The password prompt is hidden; examples use a fresh username `alice`.
The login command uses `--data '@-'` to remove the line ending PowerShell adds
to stdin; URI-encoded password characters are preserved.

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$base = 'http://127.0.0.1:8000'
$securePassword = Read-Host 'Password (12-128 characters, not only whitespace)' -AsSecureString
$password = [System.Net.NetworkCredential]::new('', $securePassword).Password

@{username='alice'; password=$password} | ConvertTo-Json -Compress | curl.exe --silent --show-error --fail-with-body "$base/auth/register" -H 'Content-Type: application/json' --data-binary '@-'

$loginBody = 'username=alice&password=' + [Uri]::EscapeDataString($password)
$login = $loginBody | curl.exe --silent --show-error --fail-with-body "$base/auth/login" -H 'Content-Type: application/x-www-form-urlencoded' --data '@-' | ConvertFrom-Json
$token = $login.access_token
$password = $null
$loginBody = $null
$securePassword = $null

curl.exe --silent --show-error --fail-with-body "$base/users/me" -H "Authorization: Bearer $token"
$note = @{title='Study plan'; body='Review Argon2 and SQL parameters'} | ConvertTo-Json -Compress | curl.exe --silent --show-error --fail-with-body "$base/notes" -H "Authorization: Bearer $token" -H 'Content-Type: application/json' --data-binary '@-' | ConvertFrom-Json
$id = $note.id
curl.exe --silent --show-error --fail-with-body "$base/notes?limit=10&offset=0&q=Argon2" -H "Authorization: Bearer $token"
curl.exe --silent --show-error --fail-with-body "$base/notes/$id" -H "Authorization: Bearer $token"
@{body='Updated study notes'} | ConvertTo-Json -Compress | curl.exe --silent --show-error --fail-with-body -X PATCH "$base/notes/$id" -H "Authorization: Bearer $token" -H 'Content-Type: application/json' --data-binary '@-'
curl.exe --silent --show-error --fail-with-body -X DELETE "$base/notes/$id" -H "Authorization: Bearer $token"
curl.exe --silent --show-error --fail-with-body "$base/health"
```

Use a recent curl supporting `--fail-with-body` (7.76 or later). A second
registration of `alice` returns 409. Tokens and passwords are sensitive; avoid
sharing terminal output containing them. Clearing variables does not guarantee
that their former contents have been erased from process memory.

All 19 commands in this block were executed line by line over localhost HTTP
on Windows PowerShell 5.1 and PowerShell 7.6.5. The interactive password prompt
was supplied by a test harness using a public synthetic password. Browser
interaction and a human-entered prompt remain manual checks.

## Project layout

```text
src/notes_api/
  __init__.py           # Version 0.1.0
  config.py             # Environment settings
  database.py           # Engine, sessions, table initialization
  models.py             # SQLAlchemy User and Note
  schemas.py            # Request validation and response models
  security.py           # Argon2id and JWT
  dependencies.py       # Sessions and authenticated user
  rate_limit.py         # Local failed-login accounting
  errors.py             # Sanitized JSON error handlers
  main.py               # App factory and startup
  routers/              # Auth, users, notes
tests/                  # Isolated temporary SQLite tests
scripts/smoke_test.py    # Real localhost HTTP checks on Windows
pyproject.toml          # Python 3.14, dependencies, ruff, pytest, coverage
Dockerfile
.dockerignore
.github/workflows/ci.yml
.env.example
.gitignore
CHANGELOG.md
LICENSE
NOTES.md                # Decisions and dependency compatibility evidence
STATE.md                # Stage progress and last gate results
```

## Tests and quality gates

Install the development extra, then run in this order:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\pytest.exe -q
git diff --check
git grep -n -i -E "YOUR[_]USERNAME|Your[ ]Name|TO[D]O|FIX[M]E|change[m]e"
# When Docker is installed:
docker build -t notes-api:0.1.0 .
```

The placeholder scan must produce no matches (Git exit code 1 means no matches).

Both pytest entry points are supported. To use the literal commands, activate the
venv first (`.\.venv\Scripts\Activate.ps1`), then run `python -m pytest` or `pytest`.
Activation is optional when using the full executable paths:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\pytest.exe
```

Pytest uses `pythonpath = [".", "src"]`, a new file-based SQLite database and a
random test-only secret per test function. Temporary databases live in ignored
`.tmp/pytest`. The 90% minimum is enforced with branch coverage enabled in
`pyproject.toml`. Tests cover auth failures, JWT validation, user isolation,
pagination/search, input limits, error sanitization, rate limiting (including
concurrent attempts), and health. They do not run the Docker image or a browser.

The separate live smoke script starts the project's venv Python with Uvicorn on
a free localhost port, supplies a random environment secret and temporary SQLite
database, and checks auth, notes, ownership, pagination, and failed-login limits
over real HTTP. It prints PASS/FAIL labels without credentials, exits 0 only on
success, and stops its Windows process tree and removes the database afterward.
It uses the standard library, Windows' built-in `taskkill.exe`, and the existing
httpx development dependency. No additional dependencies are required.

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

This command was run successfully on Windows / Python 3.14.0. It does not verify
browser interaction or Docker execution, and it does not use the local notes.db.

Dependencies were installed and exercised on Windows with Python 3.14.0.
Starlette and AnyIO have explicit compatibility pins to retain the requested
httpx TestClient backend without deprecation warnings; see `NOTES.md`.
The GitHub Actions workflow targets Ubuntu and Python 3.14, with read-only
repository permissions and major-version action pins. **Hosted CI has not run
as part of local development; its status is unverified.**

## Security

- Passwords: 12–128 characters, whitespace-only rejected. Stored only as salted
  Argon2id hashes using argon2-cffi defaults. Plaintext passwords are not logged,
  stored, or returned by application code. Passwords are never trimmed.
- Usernames: 3–32 ASCII letters, digits, or underscores. Stored lowercase, with a
  database-level case-insensitive unique constraint. Registration reports a
  duplicate name; login gives the same 401 message for unknown users and wrong
  passwords. Unknown users still incur verification against a startup dummy
  Argon2id hash. Similar expensive work is tested; constant-time behavior is
  not claimed.
- JWT: HS256 only; `sub` is a user ID; `iat` and `exp` are mandatory and validated
  by PyJWT. Default expiry is 30 minutes. Signature failures, expired tokens,
  missing claims, and invalid subjects return 401 with `WWW-Authenticate`.
  A signed token is readable by its holder and contains no password or note.
- Ownership: the current user comes from the validated token and database.
  Clients cannot set note owners. Reads, updates, and deletes query by both
  owner and ID, with 404 for foreign-owned notes. Lists and searches are scoped
  to that owner, and search text is passed as bound SQL parameters.
- Login limiting: five failed attempts for a lowercase username + client IP in
  a fixed 300-second window beginning at the first failure. Later requests get
  429 with integer `Retry-After`, including correct credentials while blocked.
  Success before blocking clears the counter. A lock serializes verification
  and accounting, so concurrent attempts cannot bypass the count. At most 10000
  active failed-login keys are held; at capacity, new keys receive 429 until
  space expires. This can deny legitimate logins under deliberate saturation.
- The limiter is **in memory, per process**, resets on restart, and is not shared
  by workers/hosts. It serializes login verification and limits throughput.
  It does not stop distributed guessing, registration abuse, or general DoS.
  No production-grade rate limiting is claimed. Supplied `X-Forwarded-For` is
  ignored by application code; documented Uvicorn commands disable proxy-header
  trust. A future trusted proxy setup needs an explicit IP trust policy.
- JSON inputs have field limits and reject unknown fields. Validation responses
  omit submitted values; application error handlers hide stack traces from
  clients. CORS is disabled. No secret is baked into source or the image.

## Known limitations / not done

- No refresh tokens, email verification, password reset, or account management.
- No token revocation/logout list; access tokens remain usable until expiry
  unless the signing key changes or the user record is removed.
- In-memory login rate limiting only; no shared store, multi-worker accounting,
  registration limits, or IP-wide abuse detection.
- SQLite storage, no migrations, backups, full-text index, or server database.
  Concurrent writes and substring searches constrain scale. Search does not
  provide full Unicode case folding.
- No HTTPS termination. Use only localhost for this demo; public deployment
  requires TLS and appropriate infrastructure configuration.
- No whole-request body size limit, audit logging, automated dependency/security
  scanning, or external penetration test. Field limits apply after body parsing.
- Health is a liveness response, not a database-readiness probe.
- Direct dependencies are pinned; there is no complete transitive lockfile.
- Docker build/run, the interactive Swagger walkthrough, and hosted CI remain
  manual checks. Test coverage is evidence about exercised paths, not proof
  that the application has no vulnerabilities.
