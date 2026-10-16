from sqlalchemy import text


def test_health_and_foreign_keys(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    with client.app.state.session_factory() as session:
        assert session.scalar(text("PRAGMA foreign_keys")) == 1


def test_health_response_schema(client):
    schema = client.get("/openapi.json").json()
    response = schema["paths"]["/health"]["get"]["responses"]["200"]
    response_schema = response["content"]["application/json"]["schema"]
    assert response_schema.get("$ref") == "#/components/schemas/HealthResponse"
    health_schema = schema["components"]["schemas"]["HealthResponse"]
    assert health_schema["required"] == ["status"]
    assert health_schema["properties"]["status"]["const"] == "ok"
    assert health_schema["properties"]["status"]["type"] == "string"
    assert "additionalProperties" not in health_schema


def test_reject_unknown_fields_and_hide_password(client, password):
    response = client.post(
        "/auth/register",
        json={"username": "alice", "password": password, "admin": True},
    )
    assert response.status_code == 422
    assert password not in response.text
    assert response.json()["error"]["details"][0]["type"] == "extra_forbidden"


def test_validation_error_does_not_echo_password(client):
    response = client.post(
        "/auth/register", json={"username": "alice", "password": "sensitive"}
    )
    assert response.status_code == 422
    assert "sensitive" not in response.text


def test_unhandled_error_is_generic(client):
    @client.app.get("/test-error")
    def fail():
        raise RuntimeError("private internal details")

    response = client.get("/test-error")
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Internal server error",
            "details": [],
        }
    }


def test_routing_errors_consistent(client):
    for method, path, status in [("GET", "/missing", 404), ("POST", "/health", 405)]:
        response = client.request(method, path)
        assert response.status_code == status
        assert response.json()["error"]["code"] == f"http_{status}"


def test_cors_disabled(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_swagger_oauth2_schema(client):
    schema = client.get("/openapi.json").json()
    flow = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]
    assert flow["password"]["tokenUrl"] == "auth/login"
    assert client.get("/docs").status_code == 200
    errors = schema["paths"]["/auth/register"]["post"]["responses"]["422"]
    assert errors["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ErrorResponse"
    )
    patch_title = schema["components"]["schemas"]["NotePatch"]["properties"]["title"]
    assert patch_title["type"] == "string"


def test_login_unknown_and_repeated_fields(client):
    response = client.post(
        "/auth/login", data={"username": "alice", "password": "wrong", "admin": "true"}
    )
    assert response.status_code == 422
    response = client.post(
        "/auth/login",
        content="username=alice&password=wrong&password=other",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 422


def test_bad_json_and_missing_form_fields(client):
    response = client.post(
        "/auth/register",
        content='{"password":',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    response = client.post("/auth/login", data={"username": "alice"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
