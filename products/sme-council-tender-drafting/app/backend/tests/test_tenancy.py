"""Tenant isolation: one customer can never see or change another's data (definition of done 1)."""
from .conftest import sign_up


def _two_tenants(new_client):
    a, b = new_client(), new_client()
    sign_up(a, email="a@alpha.test", company="Alpha")
    sign_up(b, email="b@beta.test", company="Beta")
    note = a.post("/api/vehicle", json={"title": "Alpha secret", "body": "pricing plan"}).json()
    return a, b, note


def test_other_tenant_cannot_list_read_update_delete_or_summarize(new_client):
    a, b, note = _two_tenants(new_client)
    assert b.get("/api/vehicle").json() == {"items": [], "total": 0}
    url = f"/api/vehicle/{note['id']}"
    assert b.get(url).status_code == 404
    assert b.put(url, json={"title": "hacked", "body": ""}).status_code == 404
    assert b.delete(url).status_code == 404
    assert b.post(f"{url}/summarize").status_code == 404
    still = a.get(url).json()
    assert still["title"] == "Alpha secret" and still["body"] == "pricing plan" and still["summary"] is None


def test_export_contains_only_own_tenant(new_client):
    a, b, _ = _two_tenants(new_client)
    b.post("/api/vehicle", json={"title": "Beta note"})
    exported = b.get("/api/account/export").json()
    assert exported["packs"] == [] and [u["email"] for u in exported["users"]] == ["b@beta.test"]
    assert [u["email"] for u in exported["users"]] == ["b@beta.test"]


def test_crud_for_own_notes(owner):
    client, _ = owner
    created = client.post("/api/vehicle", json={"title": " First ", "body": "hello"})
    assert created.status_code == 201
    note = created.json()
    assert note["title"] == "First"
    updated = client.put(f"/api/vehicle/{note['id']}", json={"title": "Renamed", "body": "changed"}).json()
    assert updated["title"] == "Renamed"
    assert client.get("/api/vehicle").json()["total"] == 1
    assert client.delete(f"/api/vehicle/{note['id']}").status_code == 204
    assert client.get(f"/api/vehicle/{note['id']}").status_code == 404


def test_listing_is_bounded(owner):
    client, _ = owner
    assert client.get("/api/vehicle?limit=101").status_code == 422
    assert client.get("/api/vehicle?limit=0").status_code == 422


def test_notes_with_the_same_timestamp_page_in_a_stable_order(app, owner):
    from datetime import datetime, timezone
    from .vehicle import Item
    client, me = owner
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with app.state.db.sessions() as db:
        for i in range(7):  # one transaction (like "Add samples"): identical created_at
            db.add(Item(tenant_id=me["tenant"]["id"], created_by=me["user"]["id"], title=f"n{i}", body="", created_at=stamp))
        db.commit()
    seen = []
    for offset in (0, 3, 6):
        seen += [n["id"] for n in client.get(f"/api/vehicle?limit=3&offset={offset}").json()["items"]]
    assert len(seen) == 7 and len(set(seen)) == 7
    assert seen == sorted(seen, reverse=True)
