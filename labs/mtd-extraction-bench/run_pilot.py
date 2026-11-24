"""Send each of the 5 pilot docs to Azure OpenAI exactly once (1 retry on transport error only)."""
import base64, json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path
import gen, score

HERE = Path(__file__).parent
DATA, RES = HERE / "data", HERE / "results"
DOCS = {"clean_pdf": "clean_pdf.pdf", "scan_image": "scan_image.jpg", "phone_photo": "phone_photo.jpg",
        "csv_export": "csv_export.csv", "messy_sheet": "messy_sheet.xlsx"}
MAX_OUT = 8000
PROMPT = f"""You are extracting transactions for a UK sole trader preparing HMRC Making Tax Digital quarterly updates (tax year 2026/27, 6 Apr 2026 to 5 Apr 2027). The document is a bank statement or an owner-made spreadsheet. Extract EVERY transaction line (not the brought-forward balance row).
Return ONLY JSON: {{"lines":[{{"date":"YYYY-MM-DD","description":"as written","amount":<signed number, money in positive, money out negative>,"balance":<running balance or null if not shown>,"category":"<one of {gen.CATS}>","confidence":<0 to 1>}}]}}
Categories: turnover=business income; cost_of_goods=materials/stock; wages=staff pay; car_van_travel; premises=rent/utilities; repairs; phone_office=phone/stationery; advertising; interest_bank_charges; professional_fees=accountant etc; other_expenses=other allowable business costs; drawings_personal=owner's private spending; transfer=between own accounts.
Confidence should reflect how sure you are of the category and the figures. If a date has no year use 2026 or 2027 to fit the tax year. No commentary."""


def doc_input(name):
    p = DATA / DOCS[name]
    if p.suffix == ".jpg":
        url = "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()
        return [{"type": "input_text", "text": PROMPT}, {"type": "input_image", "image_url": url}]
    if p.suffix == ".pdf":
        txt = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, check=True).stdout
    elif p.suffix == ".xlsx":
        import openpyxl
        ws = openpyxl.load_workbook(p).active
        txt = "\n".join("\t".join("" if c is None else str(c) for c in row) for row in ws.iter_rows(values_only=True))
    else:
        txt = p.read_text()
    return [{"type": "input_text", "text": PROMPT + "\n\nDOCUMENT:\n" + txt}]


def call(content, effort=True):
    body = {"model": os.environ["AZURE_OPENAI_DEPLOYMENT"], "max_output_tokens": MAX_OUT,
            "input": [{"role": "user", "content": content}]}
    if effort:
        body["reasoning"] = {"effort": "low"}
    req = urllib.request.Request(os.environ["AZURE_OPENAI_ENDPOINT"], data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def call_robust(content):
    effort, transport_retried = True, False
    while True:
        try:
            return call(content, effort), effort
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code == 400 and effort and "reasoning" in msg.lower():
                effort = False; continue          # API rejects reasoning param: fall back
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if transport_retried:
                raise RuntimeError(f"transport error after retry: {e}")
            transport_retried = True; time.sleep(5)


def parse(resp):
    text = "".join(c.get("text", "") for o in resp.get("output", []) if o.get("type") == "message"
                   for c in o.get("content", []) if c.get("type") == "output_text")
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`").removeprefix("json").strip()
    return json.loads(s), text


def main():
    out_path = RES / "pilot.json"
    if out_path.exists() and "--force" not in sys.argv:
        sys.exit("pilot.json exists: pilot is one-shot (cost control). Use score step or --force.")
    gen.build(DATA); RES.mkdir(exist_ok=True)
    runs, parsed = {}, {}
    for name in DOCS:
        t0 = time.time(); rec = {"file": DOCS[name]}
        try:
            resp, effort = call_robust(doc_input(name))
            u = resp.get("usage", {})
            rec.update(latency_s=round(time.time() - t0, 1), reasoning_effort_low_accepted=effort,
                       input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"),
                       reasoning_tokens=(u.get("output_tokens_details") or {}).get("reasoning_tokens"),
                       status=resp.get("status"))
            try:
                raw = "".join(c.get("text", "") for o in resp.get("output", []) if o.get("type") == "message"
                              for c in o.get("content", []) if c.get("type") == "output_text")
                (RES / f"rawtext_{name}.txt").write_text(raw)  # keep model text even if it fails to parse
                parsed[name], raw = parse(resp)
                (RES / f"raw_{name}.json").write_text(json.dumps(parsed[name], indent=1))
            except Exception as e:
                rec["parse_error"] = str(e)[:200]; parsed[name] = {"lines": []}
                pass
        except Exception as e:
            rec.update(error=str(e)[:300], latency_s=round(time.time() - t0, 1)); parsed[name] = {"lines": []}
        runs[name] = rec; print(name, {k: v for k, v in rec.items() if k != "file"}, flush=True)
    tot = {k: sum(r.get(k) or 0 for r in runs.values()) for k in ("input_tokens", "output_tokens", "reasoning_tokens", "latency_s")}
    out_path.write_text(json.dumps({"model": os.environ.get("AZURE_OPENAI_DEPLOYMENT"), "max_output_tokens": MAX_OUT,
                                    "runs": runs, "totals": tot, "scores": score.score_all(DATA, parsed),
                                    "assumptions": score.ASSUMP, "threshold": score.THRESHOLD}, indent=1))
    print("totals", tot)


if __name__ == "__main__":
    main()
