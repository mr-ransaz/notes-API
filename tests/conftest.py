import secrets
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from notes_api.config import Settings
from notes_api.main import create_app


def pytest_configure(config: pytest.Config) -> None:
    # Pytest creates --basetemp without creating its parent directory.
    temporary_root = config.rootpath / ".tmp"
    temporary_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    (temporary_root / "pytest").mkdir(mode=0o700, parents=True, exist_ok=True)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        secret_key=secrets.token_urlsafe(48),
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        access_token_expire_minutes=30,
    )


@pytest.fixture
def app(settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def password() -> str:
    return secrets.token_urlsafe(18)


@pytest.fixture
def auth(client, password) -> dict[str, str]:
    response = client.post(
        "/auth/register", json={"username": "alice", "password": password}
    )
    assert response.status_code == 201
    response = client.post(
        "/auth/login", data={"username": "alice", "password": password}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
