from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from sqlalchemy import select

from notes_api.models import User
from notes_api.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_register_login_me(client, password, settings):
    response = client.post(
        "/auth/register", json={"username": "Alice_1", "password": password}
    )
    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "alice_1"}
    assert "password" not in response.text
    with client.app.state.session_factory() as session:
        user = session.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(password, user.password_hash)
        assert password not in user.password_hash
    response = client.post(
        "/auth/login", data={"username": "ALICE_1", "password": password}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"
    claims = jwt.decode(
        token, settings.secret_key.get_secret_value(), algorithms=["HS256"]
    )
    assert claims["sub"] == "1"
    assert claims["exp"] - claims["iat"] == 30 * 60
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.json() == {"id": 1, "username": "alice_1"}


def test_duplicate_case_insensitive(client, password):
    for username, status in [("Alice", 201), ("aLiCe", 409)]:
        response = client.post(
            "/auth/register", json={"username": username, "password": password}
        )
        assert response.status_code == status
    assert (
        client.post(
            "/auth/login", data={"username": "alice", "password": password}
        ).status_code
        == 200
    )


@pytest.mark.parametrize("password", ["short", " " * 12, "x" * 129, ""])
def test_reject_weak_password(client, password):
    response = client.post(
        "/auth/register", json={"username": "alice", "password": password}
    )
    assert response.status_code == 422
    assert "input" not in response.text
    assert "ctx" not in response.text


@pytest.mark.parametrize("password", ["x" * 12, "x" * 128])
def test_password_length_boundaries(client, password):
    assert (
        client.post(
            "/auth/register", json={"username": "alice", "password": password}
        ).status_code
        == 201
    )


@pytest.mark.parametrize(
    "username", ["ab", "a" * 33, "a-b", "éabc", " abc", "a\n", "abc\n"]
)
def test_invalid_username(client, password, username):
    assert (
        client.post(
            "/auth/register", json={"username": username, "password": password}
        ).status_code
        == 422
    )


def test_wrong_and_unknown_user_same_error_and_work(client, password, auth):
    with patch(
        "notes_api.routers.auth.verify_password", wraps=verify_password
    ) as verify:
        wrong = client.post(
            "/auth/login", data={"username": "alice", "password": "wrong"}
        )
        unknown = client.post(
            "/auth/login", data={"username": "unknown", "password": "wrong"}
        )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.headers["www-authenticate"] == "Bearer"
    assert verify.call_count == 2
    assert verify.call_args_list[1].args[1] == client.app.state.dummy_hash


def test_unknown_user_fails_even_if_dummy_password_verifies(client):
    with patch("notes_api.routers.auth.verify_password", return_value=True):
        assert (
            client.post(
                "/auth/login", data={"username": "unknown", "password": "anything"}
            ).status_code
            == 401
        )


@pytest.mark.parametrize("field", ["username", "password"])
def test_login_input_limits(client, field):
    data = {"username": "alice", "password": "wrong"}
    data[field] = "x" * 129
    assert client.post("/auth/login", data=data).status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"iat": datetime.now(UTC) + timedelta(hours=1)},
        {"sub": "missing"},
        {"sub": "0"},
        {"sub": "01"},
        {"sub": "1" * 20},
        {"sub": "9223372036854775808"},
        {"sub": "١"},
        {"sub": "999"},
        {"sub": 1},
    ],
)
def test_invalid_claims(client, settings, change):
    claims = {
        "sub": "1",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=1),
    }
    claims.update(change)
    token = jwt.encode(
        claims, settings.secret_key.get_secret_value(), algorithm="HS256"
    )
    assert (
        client.get(
            "/users/me", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 401
    )


@pytest.mark.parametrize("claim", ["sub", "iat", "exp"])
def test_required_claims(client, settings, claim):
    claims = {"sub": "1", "iat": datetime.now(UTC), "exp": datetime.now(UTC)}
    del claims[claim]
    token = jwt.encode(
        claims, settings.secret_key.get_secret_value(), algorithm="HS256"
    )
    assert (
        client.get(
            "/users/me", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 401
    )


def test_tampered_token(client, auth):
    token = auth["Authorization"].split()[1]
    header, payload, signature = token.split(".")
    signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {header}.{payload}.{signature}"},
    )
    assert response.status_code == 401


def test_reject_other_algorithm(client, settings):
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC), "iat": datetime.now(UTC)},
        settings.secret_key.get_secret_value(),
        algorithm="HS384",
    )
    assert (
        client.get(
            "/users/me", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 401
    )


@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer garbage"])
def test_missing_or_malformed_token(client, authorization):
    headers = {} if authorization is None else {"Authorization": authorization}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_stored_hash():
    assert not verify_password("anything", "invalid hash")
    assert not verify_password("wrong", hash_password("a different value"))


@pytest.mark.parametrize("user_id", [1, 2**63 - 1])
def test_token_subject_supports_sqlite_integer_bounds(settings, user_id):
    token = create_access_token(user_id, settings)
    assert decode_access_token(token, settings) == user_id
