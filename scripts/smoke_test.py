"""Exercise a fresh Uvicorn process over localhost HTTP on Windows."""

import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


class SmokeFailure(Exception):
    """A safe, predefined failure label, without response or credential data."""


def check(label: str, passed: bool) -> None:
    if not passed:
        raise SmokeFailure(label)
    print(f"PASS {label}", flush=True)


def wait_ready(process: subprocess.Popen, url: str) -> None:
    deadline = time.monotonic() + 20
    with httpx.Client(base_url=url, timeout=1, trust_env=False) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise SmokeFailure("server startup")
            try:
                response = client.get("/health")
            except httpx.TransportError:
                time.sleep(0.1)
                continue
            if response.status_code == 200:
                return
            time.sleep(0.1)
    raise SmokeFailure("server readiness timeout")


def stop_server(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    # Windows' venv launcher can spawn a second Python process. Stop the whole
    # owned tree before waiting, so SQLite handles cannot survive the launcher.
    result = subprocess.run(
        ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    if result.returncode != 0:
        process.kill()
        process.wait(timeout=5)
        raise SmokeFailure("server process-tree cleanup")
    process.wait(timeout=5)


@contextmanager
def temporary_directory() -> Iterator[Path]:
    temporary_root = ROOT / ".tmp"
    temporary_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="smoke-", dir=temporary_root)
    try:
        yield Path(temporary.name)
    finally:
        # Windows may release the child's SQLite handles shortly after taskkill
        # returns. Retry only this owned directory, with a bounded deadline.
        deadline = time.monotonic() + 5
        while True:
            try:
                temporary.cleanup()
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise SmokeFailure("temporary SQLite cleanup") from None
                time.sleep(0.1)
            else:
                break


@contextmanager
def running_server() -> Iterator[str]:
    with temporary_directory() as directory:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.upper().startswith("NOTES_API_")
        }
        database = directory / "smoke.db"
        environment["NOTES_API_SECRET_KEY"] = secrets.token_urlsafe(48)
        environment["NOTES_API_DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
        environment["NOTES_API_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
        environment["PYTHONPATH"] = str(ROOT / "src")
        url = f"http://127.0.0.1:{port}"
        process = subprocess.Popen(
            [
                str(PYTHON),
                "-m",
                "uvicorn",
                "notes_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-proxy-headers",
                "--no-access-log",
            ],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            wait_ready(process, url)
            yield url
        finally:
            stop_server(process)
    check("server stopped and temporary SQLite removed", not database.exists())


def run_checks(client: httpx.Client) -> None:
    password = secrets.token_urlsafe(24)
    alice = {"username": "alice", "password": password}
    response = client.get("/health")
    check("GET /health returns 200", response.status_code == 200)
    response = client.post("/auth/register", json=alice)
    check("register alice returns 201", response.status_code == 201)
    response = client.post("/auth/register", json=alice)
    check("duplicate registration returns 409", response.status_code == 409)
    response = client.post(
        "/auth/register", json={"username": "weak_user", "password": "short"}
    )
    check("weak password returns 422", response.status_code == 422)

    response = client.post("/auth/login", data=alice)
    check("alice form login returns 200", response.status_code == 200)
    token = response.json().get("access_token")
    check(
        "alice receives a bearer token",
        isinstance(token, str)
        and bool(token)
        and response.json()["token_type"] == "bearer",
    )
    auth = {"Authorization": f"Bearer {token}"}
    response = client.get("/users/me", headers=auth)
    check(
        "GET /users/me identifies alice",
        response.status_code == 200 and response.json()["username"] == "alice",
    )
    check("missing token returns 401", client.get("/users/me").status_code == 401)
    payload, signature = token.rsplit(".", 1)
    signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    response = client.get(
        "/users/me", headers={"Authorization": f"Bearer {payload}.{signature}"}
    )
    check("tampered token returns 401", response.status_code == 401)

    response = client.post(
        "/notes", headers=auth, json={"title": "Smoke needle", "body": "HTTP content"}
    )
    check("create note returns 201", response.status_code == 201)
    note_id = response.json()["id"]
    response = client.get("/notes", headers=auth)
    check(
        "list includes alice's note",
        response.status_code == 200
        and [note["id"] for note in response.json()] == [note_id],
    )
    response = client.get("/notes", headers=auth, params={"q": "needle"})
    check(
        "search matches the note",
        response.status_code == 200
        and [note["id"] for note in response.json()] == [note_id],
    )
    response = client.get("/notes", headers=auth, params={"q": "absent phrase"})
    check(
        "search excludes nonmatches",
        response.status_code == 200 and response.json() == [],
    )
    response = client.patch(
        f"/notes/{note_id}", headers=auth, json={"body": "Updated HTTP content"}
    )
    check(
        "PATCH updates the note",
        response.status_code == 200
        and response.json()["body"] == "Updated HTTP content",
    )

    bob = {"username": "bob", "password": secrets.token_urlsafe(24)}
    response = client.post("/auth/register", json=bob)
    check("register bob returns 201", response.status_code == 201)
    response = client.post("/auth/login", data=bob)
    check("bob form login returns 200", response.status_code == 200)
    bob_auth = {"Authorization": f"Bearer {response.json()['access_token']}"}
    for method, data in [
        ("GET", None),
        ("PATCH", {"body": "Unauthorized"}),
        ("DELETE", None),
    ]:
        response = client.request(
            method, f"/notes/{note_id}", headers=bob_auth, json=data
        )
        check(
            f"bob {method} of alice's existing note returns 404",
            response.status_code == 404,
        )
    response = client.get(f"/notes/{note_id}", headers=auth)
    check(
        "alice's note survives bob's attempts unchanged",
        response.status_code == 200
        and response.json()["body"] == "Updated HTTP content",
    )

    for number in range(2):
        response = client.post(
            "/notes", headers=auth, json={"title": f"Page {number + 1}"}
        )
        check(
            f"create pagination note {number + 1} returns 201",
            response.status_code == 201,
        )
    response = client.get("/notes", headers=auth, params={"limit": 2})
    check(
        "limit=2 returns two of three notes",
        response.status_code == 200 and len(response.json()) == 2,
    )
    response = client.get("/notes", headers=auth, params={"limit": 101})
    check("limit=101 returns 422", response.status_code == 422)
    response = client.delete(f"/notes/{note_id}", headers=auth)
    check(
        "delete note returns 204 with no body",
        response.status_code == 204 and not response.content,
    )
    response = client.get(f"/notes/{note_id}", headers=auth)
    check("deleted note returns 404", response.status_code == 404)

    for attempt in range(1, 6):
        response = client.post(
            "/auth/login", data={"username": "alice", "password": password + "!"}
        )
        check(f"wrong login {attempt} returns 401", response.status_code == 401)
    response = client.post(
        "/auth/login", data={"username": "alice", "password": password + "!"}
    )
    retry_after = response.headers.get("Retry-After", "")
    check(
        "wrong login 6 returns 429 with Retry-After",
        response.status_code == 429
        and retry_after.isdecimal()
        and 1 <= int(retry_after) <= 300,
    )


def main() -> int:
    try:
        with (
            running_server() as url,
            httpx.Client(base_url=url, timeout=5, trust_env=False) as client,
        ):
            run_checks(client)
    except SmokeFailure as exc:
        print(f"FAIL {exc}", flush=True)
        return 1
    except (Exception, KeyboardInterrupt) as exc:
        # Do not echo response bodies, credentials, or raw exception messages.
        print(f"FAIL smoke harness ({type(exc).__name__})", flush=True)
        return 1
    print("PASS all live smoke checks", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
