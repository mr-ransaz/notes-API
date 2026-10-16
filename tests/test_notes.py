import pytest


def create_note(client, auth, title="First note", body="Private content"):
    response = client.post("/notes", headers=auth, json={"title": title, "body": body})
    assert response.status_code == 201
    return response.json()


def test_note_lifecycle(client, auth):
    note = create_note(client, auth)
    assert note == {"id": 1, "title": "First note", "body": "Private content"}
    assert client.get("/notes/1", headers=auth).json() == note
    assert client.get("/notes", headers=auth).json() == [note]
    response = client.patch("/notes/1", headers=auth, json={"title": "Updated"})
    assert response.status_code == 200
    assert response.json() == {**note, "title": "Updated"}
    response = client.patch("/notes/1", headers=auth, json={"body": ""})
    assert response.status_code == 200
    assert response.json()["body"] == ""
    assert client.get("/notes/1", headers=auth).json()["title"] == "Updated"
    response = client.delete("/notes/1", headers=auth)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/notes/1", headers=auth).status_code == 404
    assert client.get("/notes", headers=auth).json() == []


def test_body_optional_and_unicode(client, auth):
    response = client.post("/notes", headers=auth, json={"title": "Заметка 📝"})
    assert response.status_code == 201
    assert response.json()["body"] == ""
    assert client.get("/notes/1", headers=auth).json()["title"] == "Заметка 📝"


def test_foreign_note_hidden_for_all_operations(client, auth, password):
    note = create_note(client, auth)
    assert (
        client.post(
            "/auth/register", json={"username": "bob", "password": password}
        ).status_code
        == 201
    )
    token = client.post(
        "/auth/login", data={"username": "bob", "password": password}
    ).json()["access_token"]
    other_auth = {"Authorization": f"Bearer {token}"}
    assert client.get("/notes", headers=other_auth).json() == []
    assert client.get("/notes?q=Private", headers=other_auth).json() == []
    for method, kwargs in [
        ("GET", {}),
        ("PATCH", {"json": {"body": "stolen"}}),
        ("DELETE", {}),
    ]:
        foreign = client.request(method, "/notes/1", headers=other_auth, **kwargs)
        missing = client.request(method, "/notes/999", headers=other_auth, **kwargs)
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()
    assert client.get("/notes/1", headers=auth).json() == note
    assert (
        client.patch("/notes/1", headers=auth, json={"body": "Still mine"}).status_code
        == 200
    )
    assert client.delete("/notes/1", headers=auth).status_code == 204


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_missing_note(client, auth, method):
    kwargs = {"json": {"title": "Updated"}} if method == "PATCH" else {}
    assert (
        client.request(method, "/notes/999", headers=auth, **kwargs).status_code == 404
    )


def test_pagination(client, auth):
    assert client.get("/notes", headers=auth).json() == []
    for number in range(23):
        create_note(client, auth, title=f"Note {number}")
    notes = client.get("/notes", headers=auth).json()
    assert len(notes) == 20
    assert [note["id"] for note in notes] == list(range(1, 21))
    notes = client.get("/notes?limit=2&offset=3", headers=auth).json()
    assert [note["id"] for note in notes] == [4, 5]
    assert len(client.get("/notes?limit=100", headers=auth).json()) == 23
    assert client.get("/notes?offset=23", headers=auth).json() == []
    assert client.get("/notes?offset=9223372036854775807", headers=auth).json() == []


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=-1",
        "limit=101",
        "limit=no",
        "offset=-1",
        "offset=1.5",
        "offset=9223372036854775808",
        "q=" + "x" * 201,
        "unknown=value",
    ],
)
def test_invalid_pagination_and_query(client, auth, query):
    assert client.get(f"/notes?{query}", headers=auth).status_code == 422


def test_search_title_body_and_literal_wildcards(client, auth):
    create_note(client, auth, title="Security", body="Argon2")
    create_note(client, auth, title="Shopping", body="security book")
    create_note(client, auth, title="100%_done", body="quote ' and slash /")
    matches = client.get("/notes", headers=auth, params={"q": "SECURITY"}).json()
    assert [note["id"] for note in matches] == [1, 2]
    for term in ["%", "_", "'", "/"]:
        assert [
            note["id"]
            for note in client.get("/notes", headers=auth, params={"q": term}).json()
        ] == [3]
    response = client.get("/notes", headers=auth, params={"q": "' OR 1=1 --"})
    assert response.status_code == 200
    assert response.json() == []
    assert len(client.get("/notes?q=", headers=auth).json()) == 3
    matches = client.get(
        "/notes", headers=auth, params={"q": "security", "limit": 1, "offset": 1}
    ).json()
    assert [note["id"] for note in matches] == [2]


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"title": ""},
        {"title": " "},
        {"title": "x" * 201},
        {"title": "Note", "body": "x" * 10001},
        {"title": None},
        {"title": "Note", "body": None},
        {"title": 123},
        {"title": "Note", "owner_id": 2},
    ],
)
def test_create_validation(client, auth, data):
    assert client.post("/notes", headers=auth, json=data).status_code == 422
    assert client.get("/notes", headers=auth).json() == []


def test_note_length_boundaries(client, auth):
    note = create_note(client, auth, title="x" * 200, body="x" * 10000)
    assert len(note["title"]) == 200
    assert len(note["body"]) == 10000
    assert (
        client.patch(
            "/notes/1", headers=auth, json={"title": "y" * 200, "body": "y" * 10000}
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"title": None},
        {"body": None},
        {"title": ""},
        {"title": " "},
        {"title": "x" * 201},
        {"body": "x" * 10001},
        {"body": 123},
        {"owner_id": 2},
    ],
)
def test_patch_validation_preserves_note(client, auth, data):
    original = create_note(client, auth)
    assert client.patch("/notes/1", headers=auth, json=data).status_code == 422
    assert client.get("/notes/1", headers=auth).json() == original


@pytest.mark.parametrize("note_id", ["0", "-1", "abc", "9223372036854775808"])
def test_invalid_note_id(client, auth, note_id):
    assert client.get(f"/notes/{note_id}", headers=auth).status_code == 422


@pytest.mark.parametrize(
    ("method", "path", "data"),
    [
        ("POST", "/notes", {"title": "Note"}),
        ("GET", "/notes", None),
        ("GET", "/notes/1", None),
        ("PATCH", "/notes/1", {"title": "Updated"}),
        ("DELETE", "/notes/1", None),
    ],
)
def test_notes_require_authentication(client, method, path, data):
    assert client.request(method, path, json=data).status_code == 401
