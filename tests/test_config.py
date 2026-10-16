import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from notes_api.config import Settings
from notes_api.main import create_app


def test_missing_secret_refuses_startup(monkeypatch, tmp_path):
    monkeypatch.delenv("NOTES_API_SECRET_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError), TestClient(create_app()):
        pass


def test_startup_reads_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("NOTES_API_SECRET_KEY", secrets.token_urlsafe(48))
    monkeypatch.setenv(
        "NOTES_API_DATABASE_URL", f"sqlite:///{(tmp_path / 'env.db').as_posix()}"
    )
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("secret", ["", "short", " " * 40, "REPLACE_" + "x" * 40])
def test_reject_invalid_secrets(secret):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, secret_key=secret)


@pytest.mark.parametrize("url", ["postgresql://localhost/db", "sqlite:///:memory:"])
def test_reject_unsupported_database(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, secret_key=secrets.token_urlsafe(48), database_url=url)


@pytest.mark.parametrize("minutes", [0, 1441])
def test_token_expiry_bounds(minutes):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            secret_key=secrets.token_urlsafe(48),
            access_token_expire_minutes=minutes,
        )
