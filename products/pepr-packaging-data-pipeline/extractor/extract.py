"""extract_pdf: PDF path in, prediction JSON out. Isolation: the PDF is copied into an otherwise empty temp directory and
only that copy is read. This module never opens the benchmark answer files (tested)."""
import json
import re
import shutil
import tempfile
from pathlib import Path

from . import budget as budget_mod
from . import pdfio, prompt, providers, vocab

STATUSES = ("present", "missing", "conflict")
MAX_OUTPUT_TOKENS = 6000  # after tuning: ~3x the largest output seen, never below 4000; record the value used


def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except ValueError:
        a, b = t.find("{"), t.rfind("}")
        if a < 0 or b <= a:
            raise
        return json.loads(t[a:b + 1])


def _clean_field(f, weight, warns, where):
    if not isinstance(f, dict) or f.get("status") not in STATUSES:
        warns.append(f"{where}: bad field, treated as absent")
        return None
    out = {"status": f["status"]}
    conv = (lambda v: float(v)) if weight else (lambda v: str(v))
    try:
        if f["status"] == "present":
            out["value"] = conv(f["value"])
        elif f["status"] == "conflict":
            out["conflict_values"] = [conv(v) for v in f["conflict_values"]]
    except (KeyError, TypeError, ValueError):
        warns.append(f"{where}: unreadable value, treated as absent")
        return None
    if f["status"] != "missing":
        refs = []
        for r in f.get("refs") or []:
            if isinstance(r, dict) and isinstance(r.get("page"), int) and isinstance(r.get("quote"), str):
                refs.append({"page": r["page"], "quote": r["quote"]})
        out["refs"] = refs
    return out


def clean_output(raw):
    """Shape the model answer like a truth file. Nothing is invented: unreadable fields are dropped (and then score as
    wrong), absent feature keys stay absent. ram_category is derived from the canonical material."""
    warns, comps = [], []
    for i, c in enumerate(raw.get("components") or []):
        if not isinstance(c, dict) or not isinstance(c.get("name"), str):
            warns.append(f"component {i}: skipped")
            continue
        out = {"name": c["name"]}
        for k in ("material", "colour", "weight_g"):
            f = _clean_field(c.get(k), k == "weight_g", warns, f"{c['name']}.{k}")
            if f is not None:
                out[k] = f
        feats = {}
        for k, f in (c.get("features") or {}).items() if isinstance(c.get("features"), dict) else []:
            f = _clean_field(f, False, warns, f"{c['name']}.features.{k}")
            if f is not None:
                feats[k] = f
        out["features"] = feats
        mat = out.get("material", {})
        canon = vocab.tx.canonical("material", mat["value"]) if mat.get("status") == "present" else None
        out["ram_category"] = vocab.RAM_CATEGORY.get(canon, "missing") if canon else "missing"
        comps.append(out)
    return comps, warns


def _value_key(key, v):
    if key == "weight_g":
        try:
            return float(v)
        except (TypeError, ValueError):
            return float("nan")
    c = vocab.tx.canonical(key, v) if isinstance(v, str) else None
    return c if c is not None else "\x00unlisted"


def _verified(key, field, texts):
    refs = field.get("refs") or []
    values = field.get("conflict_values") if field["status"] == "conflict" else [field.get("value")]
    if not refs or not values:
        return False
    for r in refs:
        if not 1 <= r["page"] <= len(texts):
            return False
    if key in ("material", "colour"):  # sheets may use wordings outside the vocabulary (truth aliases): only require the quote on the page
        return all(vocab.tx.norm_quote(r["quote"]) and vocab.tx.norm_quote(r["quote"]) in vocab.tx.norm_quote(texts[r["page"] - 1])
                   for r in refs)
    ok = lambda v, r: vocab.tx.quote_ok(key, _value_key(key, v), r["quote"], texts[r["page"] - 1])
    return (all(any(ok(v, r) for r in refs) for v in values)
            and all(any(ok(v, r) for v in values) for r in refs))


def drop_unverified(comps, pages, warns):
    """Safety net: on TEXT pages, drop (set to missing) a non-missing field whose quote cannot be verified against the page text
    (features and weights: the scorer's quote test; material and colour: the quote must be on the page). Never invents a value. A field citing an image page is left alone: there is no text layer."""
    texts = [p["text"] if p["mode"] == "layout_text" else None for p in pages]
    for c in comps:
        fields = [(k, c, k) for k in ("material", "colour", "weight_g") if k in c]
        fields += [(k, c["features"], k) for k in list(c["features"])]
        for key, holder, name in fields:
            f = holder[name]
            if f["status"] == "missing":
                continue
            cited = [r["page"] for r in f.get("refs", [])]
            if cited and any(1 <= n <= len(texts) and texts[n - 1] is None for n in cited):
                continue
            if key not in ("material", "colour", "weight_g") and key not in vocab.tx.VOCAB:
                verified = False
            else:
                verified = _verified(key, f, texts)
            if not verified:
                warns.append(f"{c['name']}.{key}: quote not found on the page text, dropped")
                holder[name] = {"status": "missing"}
        if c.get("material", {}).get("status") != "present":
            c["ram_category"] = "missing"
    return comps


def extract_pdf(pdf_path, provider, budget, sheet_id=None, max_output_tokens=MAX_OUTPUT_TOKENS):
    """Run one sheet. Returns the prediction dict (truth shape + `pages`, `usage`, `warnings`)."""
    sheet_id = sheet_id or Path(pdf_path).stem
    with tempfile.TemporaryDirectory(prefix="pepr-extract-") as tmp:
        copy = Path(tmp) / "sheet.pdf"
        shutil.copyfile(pdf_path, copy)
        assert [p.name for p in Path(tmp).iterdir()] == ["sheet.pdf"]
        pages = pdfio.read_pages(copy)
    system = prompt.system_prompt()
    parts = prompt.build_parts(pages)
    est_in = providers.estimate_input_tokens(system, parts)
    budget.check(est_in, max_output_tokens + int(getattr(provider, "output_headroom", 0)), label=sheet_id)
    try:
        res = provider.complete(system, parts, max_output_tokens, budget=budget, label=sheet_id)
    except providers.ProviderError as e:
        if e.may_have_run:
            budget.record(sheet_id, e.input_tokens, e.output_tokens, estimated=True, note=f"worst case after: {e}")
        elif e.input_tokens or e.output_tokens:
            budget.record(sheet_id, e.input_tokens, e.output_tokens, note=f"failed: {e}")
        raise
    if not budget_mod.served_model_matches(budget.model, res.model):
        # the deployment name is free text: the model that answered is not the one we price. Charge the most
        # expensive price in the table (the cap stays conservative) and stop the run.
        worst = budget_mod.most_expensive_model()
        budget.record(sheet_id, res.input_tokens, res.output_tokens, model=worst, served_model=res.model or "",
                      note=f"served model {res.model!r} does not match price model {budget.model!r}; priced at {worst}")
        raise providers.ProviderError(
            f"served model mismatch: deployment {budget.deployment or budget.model!r} answered as {res.model!r} but is priced "
            f"as {budget.model!r}; the call was charged at {worst} prices and the run is stopped. Fix the deployment "
            f"(AZURE_OPENAI_DEPLOYMENT_MINI / T56_DEPLOYMENT) before any further call", fatal=True)
    budget.record(sheet_id, res.input_tokens, res.output_tokens, served_model=res.model)
    modes = [{"page": p["page"], "input": p["mode"], "chars": p["chars"]} for p in pages]
    try:
        comps, warns = clean_output(parse_json(res.text))
        drop_unverified(comps, pages, warns)
    except (ValueError, AttributeError, TypeError):
        comps, warns = [], ["model answer was not valid JSON"]
    return {"sheet_id": sheet_id, "components": comps, "pages": modes, "warnings": warns,
            "usage": {"input_tokens": res.input_tokens, "output_tokens": res.output_tokens,
                      "usd": round(budget_mod.usd(res.input_tokens, res.output_tokens, budget.model), 6), "model": res.model,
                      "price_model": budget.model, "deployment": budget.deployment or budget.model}}
