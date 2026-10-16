from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from notes_api.rate_limit import LoginRateLimiter, RateLimitExceeded


def test_rate_limit_and_retry_after(client, auth, password):
    now = [100.0]
    client.app.state.login_limiter = LoginRateLimiter(clock=lambda: now[0])
    for _ in range(5):
        assert (
            client.post(
                "/auth/login", data={"username": "alice", "password": "wrong"}
            ).status_code
            == 401
        )
    with patch("notes_api.routers.auth.verify_password") as verify:
        response = client.post(
            "/auth/login", data={"username": "ALICE", "password": password}
        )
    verify.assert_not_called()
    assert response.status_code == 429
    assert response.headers["retry-after"] == "300"
    now[0] += 299.5
    response = client.post(
        "/auth/login", data={"username": "alice", "password": "wrong"}
    )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "1"
    now[0] += 0.5
    assert (
        client.post(
            "/auth/login", data={"username": "alice", "password": password}
        ).status_code
        == 200
    )


def test_success_clears_failure_count(client, auth, password):
    for _ in range(4):
        assert (
            client.post(
                "/auth/login", data={"username": "alice", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/auth/login", data={"username": "alice", "password": password}
        ).status_code
        == 200
    )
    for _ in range(5):
        assert (
            client.post(
                "/auth/login", data={"username": "alice", "password": "wrong"}
            ).status_code
            == 401
        )


def test_unknown_user_is_rate_limited_and_usernames_independent(client):
    for _ in range(5):
        assert (
            client.post(
                "/auth/login", data={"username": "unknown", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/auth/login", data={"username": "unknown", "password": "wrong"}
        ).status_code
        == 429
    )
    assert (
        client.post(
            "/auth/login", data={"username": "other", "password": "wrong"}
        ).status_code
        == 401
    )


def test_rate_limits_are_per_ip_and_ignore_forwarded_header(app):
    with TestClient(app, client=("192.0.2.1", 1000)) as first:
        for _ in range(5):
            assert (
                first.post(
                    "/auth/login", data={"username": "unknown", "password": "wrong"}
                ).status_code
                == 401
            )
        assert (
            first.post(
                "/auth/login",
                data={"username": "unknown", "password": "wrong"},
                headers={"X-Forwarded-For": "192.0.2.2"},
            ).status_code
            == 429
        )
        # Do not enter another lifespan; both transports use the running app.
        second = TestClient(app, client=("192.0.2.2", 1000))
        try:
            assert (
                second.post(
                    "/auth/login", data={"username": "unknown", "password": "wrong"}
                ).status_code
                == 401
            )
            assert (
                first.post(
                    "/auth/login", data={"username": "unknown", "password": "wrong"}
                ).status_code
                == 429
            )
        finally:
            second.close()


def test_rate_limiter_without_client_address(app):
    with TestClient(app, client=None) as client:
        assert (
            client.post(
                "/auth/login", data={"username": "unknown", "password": "wrong"}
            ).status_code
            == 401
        )


def test_bounded_state_fails_closed_and_expires():
    now = [0.0]
    limiter = LoginRateLimiter(clock=lambda: now[0], max_keys=1)
    assert limiter.authenticate(("alice", "ip"), lambda: None) is None
    with pytest.raises(RateLimitExceeded) as exc:
        limiter.authenticate(("bob", "ip"), lambda: "allowed")
    assert exc.value.retry_after == 300
    now[0] = 300
    assert limiter.authenticate(("bob", "ip"), lambda: "allowed") == "allowed"


def test_concurrent_attempts_cannot_bypass_threshold():
    limiter = LoginRateLimiter()
    calls = []

    def fail():
        calls.append(1)
        return None

    def attempt(_):
        try:
            limiter.authenticate(("alice", "ip"), fail)
        except RateLimitExceeded:
            return 429
        return 401

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(attempt, range(12)))
    assert results.count(401) == 5
    assert results.count(429) == 7
    assert len(calls) == 5


def test_verification_exception_does_not_poison_lock_or_count():
    limiter = LoginRateLimiter()

    def fail():
        raise RuntimeError("Verification unavailable")

    with pytest.raises(RuntimeError):
        limiter.authenticate(("alice", "ip"), fail)
    assert limiter.authenticate(("alice", "ip"), lambda: "ok") == "ok"
