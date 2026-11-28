"""Seed the demo tenant: the fictional firm's evidence library, the demo tender packs and the AI cache (S9). No model calls.

    DEMO_SEED_PASSWORD=... python -m eval.seed        (run from the product directory; DATABASE_URL as for the app)

Packs come from whatever files exist in demo-data/packs/ (.pdf .docx .txt .md). With none it stops with SeedError: it
never invents a pack. `demo-data/packs/manifest.json` (optional) may list {"demo": ["file", ...]}; otherwise the first 3
files in name order are the demo packs. The cache step copies every recording under
app/backend/fixtures/recorded/<task>/<key>.json into the tenant's ai_cache, so the demo shows real recorded output.
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
from pathlib import Path

PRODUCT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRODUCT / "app" / "backend"))  # the app package

FIRM = "Harrowmere Facilities Ltd (fictional)"
EVIDENCE_DIR = PRODUCT / "demo-data" / "evidence"
PACKS_DIR = PRODUCT / "demo-data" / "packs"
RECORDED_DIR = PRODUCT / "app" / "backend" / "fixtures" / "recorded"
PACK_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
DEMO_PACKS = 3


class SeedError(RuntimeError):
    pass


def category_for(name: str) -> str:
    n = name.lower()
    for word, cat in (("case-study", "case_study"), ("accreditation", "accreditation"), ("social-value", "social_value"),
                      ("company-profile", "company_facts"), ("turnover", "company_facts"), ("kpi", "company_facts")):
        if word in n:
            return cat
    return "policy"


def find_packs(packs_dir: Path = PACKS_DIR) -> list[Path]:
    files = sorted(p for p in packs_dir.glob("*") if p.is_file() and p.suffix.lower() in PACK_SUFFIXES) if packs_dir.is_dir() else []
    if not files:
        raise SeedError(f"no tender pack files in {packs_dir} (Q-20: packs are not downloaded yet; add .pdf/.docx/.txt/.md "
                        f"files there, or the synthetic packs). Nothing was seeded.")
    manifest = packs_dir / "manifest.json"
    if manifest.is_file():
        names = json.loads(manifest.read_text(encoding="utf-8")).get("demo", [])
        if not names:
            raise SeedError("manifest.json has no \"demo\" packs listed: refusing to seed zero packs")
        root = packs_dir.resolve()
        chosen = [packs_dir / n for n in names]
        escaped = [n for n, p in zip(names, chosen) if not p.resolve().is_relative_to(root)]
        if escaped:
            raise SeedError("manifest.json names paths outside the packs directory: " + ", ".join(escaped))
        missing = [str(p.name) for p in chosen if not p.is_file()]
        if missing:
            raise SeedError("manifest.json lists demo packs that do not exist: " + ", ".join(missing))
        return chosen[:DEMO_PACKS]
    return files[:DEMO_PACKS]


def _error_of(r) -> str:
    try:
        return str(r.json().get("error"))
    except Exception:
        return "non-JSON body"


def _upload(client, url: str, path: Path, **form):
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return client.post(url, files={"file": (path.name, path.read_bytes(), mime)}, data=form)


def load_cache(sessions, tenant_id, recorded_dir: Path = RECORDED_DIR) -> int:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.tender_models import AICache
    n = 0
    with sessions() as db:
        for f in sorted(recorded_dir.glob("*/*.json")) if recorded_dir.is_dir() else []:
            data = json.loads(f.read_text(encoding="utf-8"))
            out = data["output"] if isinstance(data, dict) and "output" in data else data
            tin, tout = (data.get("input_tokens", 0), data.get("output_tokens", 0)) if isinstance(data, dict) else (0, 0)
            db.execute(pg_insert(AICache).values(tenant_id=tenant_id, key=f.stem, output_json=out, input_tokens=tin,
                                                 output_tokens=tout).on_conflict_do_nothing())
            n += 1
        db.commit()
    return n


def evidence_docs(evidence_dir: Path) -> list[Path]:
    """Evidence files in upload order (this order fixes the E-n numbers the eval keys cite). README.md describes the
    library, including its deliberate gaps, so uploading it would leak the trap answers into retrieval: it is skipped."""
    return [p for p in sorted(evidence_dir.glob("*.md")) + sorted(evidence_dir.glob("*.txt")) if p.name.lower() != "readme.md"]


def seed(client, sessions, tenant_id, *, evidence_dir: Path = EVIDENCE_DIR, packs_dir: Path = PACKS_DIR,
         recorded_dir: Path = RECORDED_DIR) -> dict:
    """`client` is signed in as the demo tenant's owner. Packs are checked first, so a missing pack changes nothing."""
    packs = find_packs(packs_dir)
    docs = evidence_docs(evidence_dir)
    if not docs:
        raise SeedError(f"no evidence documents in {evidence_dir}")
    passages = 0
    for d in docs:
        r = _upload(client, "/api/evidence/documents", d, category=category_for(d.name))
        if r.status_code not in (201, 409):
            raise SeedError(f"evidence upload {d.name} failed: {r.status_code} {_error_of(r)}")
        passages += r.json().get("passages", 0) if r.status_code == 201 else 0
    listing = client.get("/api/packs")
    existing = {x.get("title"): x["id"] for x in listing.json().get("packs", [])} if listing.status_code == 200 else {}
    pack_ids = []
    for p in packs:
        if p.stem[:200] in existing:           # re-seeding must not duplicate a pack
            pack_ids.append(existing[p.stem[:200]])
            continue
        r = client.post("/api/packs", json={"title": p.stem[:200]})
        if r.status_code != 201:
            raise SeedError(f"pack create failed: {r.status_code}")
        pid = r.json()["id"]
        u = _upload(client, f"/api/packs/{pid}/documents", p)
        if u.status_code not in (201, 409):
            raise SeedError(f"pack upload {p.name} failed: {u.status_code} {_error_of(u)}")
        pack_ids.append(pid)
    return {"firm": FIRM, "evidence_documents": len(docs), "evidence_passages": passages, "packs": pack_ids,
            "cache_rows": load_cache(sessions, tenant_id, recorded_dir)}


def main() -> int:
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.config import Settings
    from app.main import create_app
    from app.models import Tenant
    password = os.environ.get("DEMO_SEED_PASSWORD")
    if not password:
        print("seed: set DEMO_SEED_PASSWORD (the demo owner's password; never put it in a file)", file=sys.stderr)
        return 2
    try:
        find_packs()  # fail before any account is created
        app = create_app(Settings())
        with TestClient(app, base_url="https://testserver", headers={"X-Requested-With": "seed"}) as client:
            r = client.post("/api/auth/signup", json={"company_name": FIRM, "email": "demo@harrowmere.example", "password": password})
            if r.status_code not in (201, 409):
                print(f"seed: sign-up failed ({r.status_code})", file=sys.stderr)
                return 1
            if r.status_code == 409:
                login = client.post("/api/auth/login", json={"email": "demo@harrowmere.example", "password": password})
                if login.status_code != 200:
                    print(f"seed: the demo account exists but sign-in failed ({login.status_code}): wrong DEMO_SEED_PASSWORD?",
                          file=sys.stderr)
                    return 1
            sessions = app.state.db.sessions
            with sessions() as db:
                tenant_id = db.scalar(select(Tenant.id).where(Tenant.name == FIRM))
            print(json.dumps(seed(client, sessions, tenant_id), indent=2))
    except SeedError as e:
        print(f"seed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
