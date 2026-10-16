# Working agreement

## Session-start protocol
1. Read this file and STATE.md before editing anything.
2. Run `git status --short`; stop if the tree is dirty. Never overwrite or
   discard existing changes.
3. Run `git log -1 --oneline`; confirm branch and Python version.
4. Inspect the relevant code, tests and docs before changing anything.
5. If STATE.md mentions a release tag, resolve it with
   `git rev-list -n 1 <tag>` (never use `^{commit}` in PowerShell).

## Rules
- Python 3.14 only. Run every Python tool through
  `.\.venv\Scripts\python.exe` (pip, ruff, pytest, project CLI/server).
  Never use global Python or global tool launchers. Git uses `git`.
- Dependencies follow the Project profile below. Every dependency change
  must be explained in NOTES.md. Dev-only tools go in the `dev` extra.
- Never log, store, print or commit real passwords, tokens, keys, .env
  files or databases. Use only public synthetic values in tests and docs.
  Never put raw exceptions or secret values into logs or responses.
- Inspect before editing; make the smallest complete fix; add meaningful
  regression tests. Never skip tests or suppress failures to pass a gate.
- README claims and captured outputs must be verified by execution.
  Clearly separate local/mocked checks from unverified external services
  (Docker, hosted CI, live network). Never claim an unrun check passed.
- No placeholders in committed files (YOUR_USERNAME, Your Name, TODO,
  changeme). Use the real values from the Project profile.
- Small Conventional Commits (feat:, fix:, test:, docs:, ci:, chore:) with
  explicit paths. Do not push, rewrite history, reset unrelated changes,
  or touch anything outside the project folder.
- Tags: follow the Project profile. Never move or delete an existing tag.
- No subagents unless the user explicitly asks.

## Gate checklist (run in this order)
1. `.\.venv\Scripts\python.exe -m ruff check .`
2. `.\.venv\Scripts\python.exe -m ruff format --check .`
3. `.\.venv\Scripts\python.exe -m pytest -q` (coverage minimum from profile)
4. `.\.venv\Scripts\pytest.exe -q`
5. `git diff --check`
6. Placeholder scan:
   `git grep -n -i -E "YOUR_USERNAME|Your Name|TODO|FIXME|changeme"`
   must be empty (except documented placeholders in .env.example).
7. Docker build only if docker exists; otherwise list as manual check.
8. Verify every runnable README example and its output/exit code.

## End of task
- Update README, NOTES.md and CHANGELOG with supported claims only.
- Update STATE.md last (max 60 lines): real gate results, last
  implementation commit, remaining unverified work.
- Commit the checkpoint, confirm a clean tree, then STOP. Print:
  `git log --oneline`, `git status`, test count and coverage, anything
  not verified, and MANUAL CHECKS.

## Project profile
- Name / repo: notes-api
- Author / license: MR Ransaz / MIT 2026
- Purpose: secure REST API for private notes (portfolio, backend/security)
- Stack and dependency policy: FastAPI, SQLAlchemy 2 + SQLite, Pydantic v2,
  argon2-cffi, PyJWT, pytest, ruff. Runtime deps pinned in pyproject.toml.
- Layout and docs location: src/notes_api/, tests/, NOTES.md and STATE.md
  in the repo root.
- Coverage minimum: 90% with branch coverage.
- Project-specific rules: every note query filters by owner_id; foreign
  notes return 404, never 403; SQL is parameterized; SECRET_KEY comes only
  from NOTES_API_SECRET_KEY, with no default in code; login errors never
  reveal whether a username exists.
- Tag policy: create no tags.