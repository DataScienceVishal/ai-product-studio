"""Control characters (NUL above all) must be a 422 at the edge, never a 500 from Postgres."""
import pytest

from tests.conftest import PASSWORD, sign_up


@pytest.mark.parametrize("field", ["title", "body"])
def test_nul_in_note_is_422(owner, field):
    client, _ = owner
    data = {"title": "ok", "body": "ok", field: "a\u0000b"}
    assert client.post("/api/notes", json=data).status_code == 422
    made = client.post("/api/notes", json={"title": "fine", "body": ""}).json()
    assert client.put(f"/api/notes/{made['id']}", json=data).status_code == 422


def test_other_control_chars_refused_but_newlines_and_tabs_allowed_in_body(owner):
    client, _ = owner
    assert client.post("/api/notes", json={"title": "t", "body": "a\x07b"}).status_code == 422
    assert client.post("/api/notes", json={"title": "a\nb", "body": ""}).status_code == 422
    ok = client.post("/api/notes", json={"title": "t", "body": "line1\nline2\tx\r\n"})
    assert ok.status_code == 201


@pytest.mark.parametrize("title", ["", "   ", "\t  "])
def test_blank_note_title_is_422(owner, title):
    client, _ = owner
    assert client.post("/api/notes", json={"title": title}).status_code == 422
    made = client.post("/api/notes", json={"title": "fine"}).json()
    assert client.put(f"/api/notes/{made['id']}", json={"title": title}).status_code == 422


def test_note_title_is_stripped(owner):
    client, _ = owner
    assert client.post("/api/notes", json={"title": "  hi  "}).json()["title"] == "hi"


@pytest.mark.parametrize("path", ["/api/auth/login", "/api/auth/password-reset/request", "/api/auth/signup"])
@pytest.mark.parametrize("email", ["a\u0000@z.test", "a@b.cc\u0000", "a@b\u0000.cc"])
def test_nul_in_email_is_422(new_client, path, email):
    client = new_client()
    body = {"email": email, "password": PASSWORD}
    if path.endswith("signup"):
        body["company_name"] = "Acme"
    if "reset" in path:
        body = {"email": email}
    response = client.post(path, json=body)
    assert response.status_code == 422, (path, response.text)


def test_nul_in_invite_email_is_422(owner):
    client, _ = owner
    assert client.post("/api/team/invitations", json={"email": "x\u0000@z.test"}).status_code == 422


def test_company_name_control_chars_are_normalised(new_client):
    client = new_client()
    body = sign_up(client, email="nul@acme.test", company="Ac\u0000me")
    assert "\x00" not in body["tenant"]["name"]


@pytest.mark.parametrize("suffix", ["\n", "\t", " \r\n"])
def test_login_and_reset_accept_email_with_trailing_whitespace(new_client, suffix):
    """Strip before the control-character check, as signup does (T-71 review): a pasted trailing newline still signs in."""
    client = new_client()
    sign_up(client, email="trail@acme.test")
    other = new_client()
    login = other.post("/api/auth/login", json={"email": "trail@acme.test" + suffix, "password": PASSWORD})
    assert login.status_code == 200, login.text
    reset = new_client().post("/api/auth/password-reset/request", json={"email": "trail@acme.test" + suffix})
    assert reset.status_code != 422, reset.text
