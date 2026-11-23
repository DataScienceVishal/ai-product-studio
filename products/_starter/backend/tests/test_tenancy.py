"""Tenant isolation: one customer can never see or change another's data (definition of done 1)."""
from .conftest import sign_up


def _two_tenants(new_client):
    a, b = new_client(), new_client()
    sign_up(a, email="a@alpha.test", company="Alpha")
    sign_up(b, email="b@beta.test", company="Beta")
    note = a.post("/api/notes", json={"title": "Alpha secret", "body": "pricing plan"}).json()
    return a, b, note


def test_other_tenant_cannot_list_read_update_delete_or_summarize(new_client):
    a, b, note = _two_tenants(new_client)
    assert b.get("/api/notes").json() == {"items": [], "total": 0}
    url = f"/api/notes/{note['id']}"
    assert b.get(url).status_code == 404
    assert b.put(url, json={"title": "hacked", "body": ""}).status_code == 404
    assert b.delete(url).status_code == 404
    assert b.post(f"{url}/summarize").status_code == 404
    still = a.get(url).json()
    assert still["title"] == "Alpha secret" and still["body"] == "pricing plan" and still["summary"] is None


def test_export_contains_only_own_tenant(new_client):
    a, b, _ = _two_tenants(new_client)
    b.post("/api/notes", json={"title": "Beta note"})
    exported = b.get("/api/account/export").json()
    assert [n["title"] for n in exported["notes"]] == ["Beta note"]
    assert [u["email"] for u in exported["users"]] == ["b@beta.test"]


def test_crud_for_own_notes(owner):
    client, _ = owner
    created = client.post("/api/notes", json={"title": " First ", "body": "hello"})
    assert created.status_code == 201
    note = created.json()
    assert note["title"] == "First"
    updated = client.put(f"/api/notes/{note['id']}", json={"title": "Renamed", "body": "changed"}).json()
    assert updated["title"] == "Renamed"
    assert client.get("/api/notes").json()["total"] == 1
    assert client.delete(f"/api/notes/{note['id']}").status_code == 204
    assert client.get(f"/api/notes/{note['id']}").status_code == 404


def test_listing_is_bounded(owner):
    client, _ = owner
    assert client.get("/api/notes?limit=101").status_code == 422
    assert client.get("/api/notes?limit=0").status_code == 422
