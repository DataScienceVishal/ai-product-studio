"""T-87: regression tests for the low items left open by the T-86 bug hunt (bugs 4 to 7)."""
import pytest

from tests.conftest import PASSWORD, sign_up

INVISIBLE = ["​", "‌", "‍", "⁠", "﻿", "­", "‎", " ​ ﻿\t"]


@pytest.mark.parametrize("blank", INVISIBLE)
def test_invisible_only_title_is_422_like_an_empty_one(owner, blank):
    client, _ = owner
    assert client.post("/api/notes", json={"title": blank}).status_code == 422
    made = client.post("/api/notes", json={"title": "fine"}).json()
    assert client.put(f"/api/notes/{made['id']}", json={"title": blank}).status_code == 422


@pytest.mark.parametrize("blank", INVISIBLE + ["   ", "\n", "\u200b"])
def test_invisible_only_body_is_normalised_to_empty(owner, blank):
    client, _ = owner
    made = client.post("/api/notes", json={"title": "t", "body": blank})
    assert made.status_code == 201
    assert made.json()["body"] == ""
    again = client.put(f"/api/notes/{made.json()['id']}", json={"title": "t", "body": blank})
    assert again.status_code == 200
    assert again.json()["body"] == ""
    assert client.post("/api/notes", json={"title": "t", "body": ""}).json()["body"] == ""


FILLERS = ["\u115f", "\u1160", "\u3164", "\uffa0", "\u2800", "\u3164\u2800 "]


@pytest.mark.parametrize("blank", FILLERS)
def test_filler_only_title_is_422(owner, blank):
    client, _ = owner
    assert client.post("/api/notes", json={"title": blank}).status_code == 422


@pytest.mark.parametrize("blank", ["\u200b", "\u3164"])
def test_invisible_only_company_name_is_422(new_client, blank):
    r = new_client().post("/api/auth/signup", json={"company_name": blank, "email": "co@example.com", "password": PASSWORD})
    assert r.status_code == 422


def test_json_invalid_detected_by_type_not_by_loc_shape():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel

    from app import errors

    class Item(BaseModel):
        n: int

    app = FastAPI()
    errors.install(app)

    @app.post("/items")
    def items(body: list[Item]):
        return {"ok": True}

    client = TestClient(app)
    # A genuine item error at index 1 has loc ("body", 1, "n"): it keeps its own message, not "not valid JSON".
    bad_item = client.post("/items", json=[{"n": 1}, {"n": "x"}])
    assert bad_item.status_code == 422
    assert "not valid JSON" not in bad_item.json()["fields"][0]["problem"]
    assert bad_item.json()["fields"][0]["field"] == "1.n"
    # A real syntax error still reads as malformed JSON.
    broken = client.post("/items", content='[{"n": ', headers={"content-type": "application/json"})
    assert broken.json()["fields"][0]["problem"] == "The request body is not valid JSON."


def test_real_text_keeps_its_zwj_and_format_characters(owner):
    client, _ = owner
    family = "\U0001F468‍\U0001F469‍\U0001F467"
    persian = "می‌خواهم"  # ZWNJ inside a word
    made = client.post("/api/notes", json={"title": family, "body": persian + "​"})
    assert made.status_code == 201
    assert made.json()["title"] == family
    assert made.json()["body"] == persian + "​"


@pytest.mark.parametrize("email", ["üser@exämple.com", "user@exämple.com", "ｕser@example.com", "user@例え.jp"])
def test_non_ascii_email_is_refused_at_signup_with_a_clear_message(new_client, email):
    r = new_client().post("/api/auth/signup", json={"company_name": "Acme", "email": email, "password": PASSWORD})
    assert r.status_code == 422
    assert "ASCII" in r.json()["fields"][0]["problem"]


def test_non_ascii_email_is_refused_in_invitations(owner):
    client, _ = owner
    r = client.post("/api/team/invitations", json={"email": "bøb@acme.test"})
    assert r.status_code == 422
    assert "ASCII" in r.json()["fields"][0]["problem"]


def test_login_with_a_non_ascii_email_just_fails(new_client):
    sign_up(new_client(), email="plain@acme.test")
    r = new_client().post("/api/auth/login", json={"email": "plaïn@acme.test", "password": PASSWORD})
    assert r.status_code == 401


def test_trailing_slash_is_a_404_not_a_redirect(owner):
    client, _ = owner
    for path in ("/api/notes/", "/api/auth/me/", "/api/team/"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 404, path
        assert "location" not in r.headers
    assert client.get("/api/notes", follow_redirects=False).status_code == 200


def test_malformed_json_does_not_name_a_field_after_the_byte_offset(owner):
    client, _ = owner
    r = client.post("/api/notes", content=b'{"title": ', headers={"content-type": "application/json"})
    assert r.status_code == 422
    fields = r.json()["fields"]
    assert fields == [{"field": "", "problem": "The request body is not valid JSON."}]


def test_a_missing_field_still_names_the_field(owner):
    client, _ = owner
    r = client.post("/api/notes", json={})
    assert r.json()["fields"][0]["field"] == "title"
