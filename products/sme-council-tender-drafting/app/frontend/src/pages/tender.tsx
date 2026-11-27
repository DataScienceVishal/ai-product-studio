// Review screens (S7). Static routes with the id in the query string (/pack?id=...), so the server needs no pattern routes (R7).
// No price or plan text anywhere on these pages.
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { api, ApiError } from "../api";
import { Alert, Button, Card, Field, Link, navigate } from "../ui";

// ---------- types (the API's shapes) ----------
export type Pack = { id: string; title: string; buyer: string; status: string; deadline: string | null; created_at: string };
export type Doc = { id: string; kind: string; filename: string; category: string | null; page_count: number; created_at: string };
export type Task = { id: string; kind: string; status: string; error_code: string | null; attempts: number };
export type Req = {
  id: string; pack_id: string; seq: number; ref: string; kind: string; text: string; word_limit: number | null; marks: number | null;
  source_page: number | null; source_quote: string | null; quote_verified: boolean; origin: string; status: string; flags: string[];
  edited: boolean;
};
export type Draft = {
  id: string; version: number; text: string; word_count: number; word_limit: number | null; cited_ids: number[];
  outside_ids: number[]; gap_count: number; flags: string[]; author: string; status: string;
};
export type Claim = { seq: number; span: string; kind: string; cited_ids: number[]; verdict: string; evidence_quote: string; reason: string };
export type Passage = { display_no: number; label: string; document: string; page_from: number; page_to: number; heading: string | null; removed: boolean; text: string };

export const errorText = (err: unknown) => (err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
const queryId = () => new URLSearchParams(window.location.search).get("id") ?? "";
const UUID = /^[0-9a-f-]{32,36}$/i;

// ---------- hooks ----------
export function useLoad<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    load().then((d) => { if (alive) { setData(d); setError(null); } }).catch((e) => { if (alive) setError(errorText(e)); });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, reload: useCallback(() => setTick((n) => n + 1), []) };
}

export const POLL_MS = 3000;
export const POLL_MAX_MS = 15000;
export const POLL_MAX_TICKS = 200;
/** Polls while `active`: one request at a time (a timeout chain, not an interval), a pause that doubles after a failure up to
 * 15 s, and a hard stop after 200 ticks. `step` returns true to keep going; the first call is one pause after `active` turns on. */
export function usePoll(step: () => Promise<boolean>, active: boolean) {
  const ref = useRef(step);
  ref.current = step;
  useEffect(() => {
    if (!active) return;
    let stopped = false;
    let delay = POLL_MS;
    let ticks = 0;
    let timer: ReturnType<typeof setTimeout>;
    const run = async () => {
      let again = true;
      try { again = await ref.current(); delay = POLL_MS; } catch { delay = Math.min(delay * 2, POLL_MAX_MS); }
      ticks += 1;
      if (!stopped && again && ticks < POLL_MAX_TICKS) timer = setTimeout(run, delay);
    };
    timer = setTimeout(run, delay);
    return () => { stopped = true; clearTimeout(timer); };
  }, [active]);
}

export type PackStatus = { pack: Pack; tasks: Task[] };
export const isBusy = (s: PackStatus | null) =>
  !!s && (["extracting", "checking"].includes(s.pack.status) || s.tasks.some((t) => t.status === "queued" || t.status === "running"));

export const STATUS_LABEL: Record<string, string> = {
  uploaded: "Uploaded", extracting: "Finding requirements", review: "Checklist to review", drafting: "Drafting", checking: "Checking claims",
  ready: "Ready to sign off", signed: "Signed off", exported: "Exported",
};
const TASK_LABEL: Record<string, string> = { extract: "Finding requirements", draft: "Drafting answers", claimcheck: "Checking claims" };

// ---------- small pieces ----------
function Badge({ tone, children }: { tone: "amber" | "red" | "green" | "slate" | "blue"; children: ReactNode }) {
  const c = { amber: "bg-amber-100 text-amber-900 border-amber-300", red: "bg-red-100 text-red-900 border-red-300",
    green: "bg-green-100 text-green-900 border-green-300", slate: "bg-slate-100 text-slate-800 border-slate-300",
    blue: "bg-blue-100 text-blue-900 border-blue-300" }[tone];
  return <span className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${c}`}>{children}</span>;
}

function Title({ children, back }: { children: ReactNode; back?: { to: string; label: string } }) {
  return (
    <div className="mb-4">
      {back && <p className="mb-1 text-sm"><Link to={back.to}>{back.label}</Link></p>}
      <h1 className="text-2xl font-bold text-slate-900">{children}</h1>
    </div>
  );
}

function NoId({ what }: { what: string }) {
  return (
    <div>
      <Title>{what}</Title>
      <Alert>There is nothing selected here. <Link to="/packs">Go to your tender packs</Link>.</Alert>
    </div>
  );
}

function ProgressLine({ status }: { status: PackStatus | null }) {
  if (!status || !isBusy(status)) return null;
  const live = status.tasks.find((t) => t.status === "queued" || t.status === "running");
  return <Alert kind="info">{live ? TASK_LABEL[live.kind] ?? "Working" : STATUS_LABEL[status.pack.status]}… this page updates by itself.</Alert>;
}

function FailedTask({ status }: { status: PackStatus | null }) {
  const failed = status && !isBusy(status) ? status.tasks[0] : null;
  if (!failed || failed.status !== "failed") return null;
  return <Alert>The last step ({TASK_LABEL[failed.kind] ?? failed.kind}) did not finish{failed.error_code ? ` (${failed.error_code})` : ""}. You can run it again.</Alert>;
}

/** Status of a pack, polled only while something is in progress. `onSettled` runs once when work stops. */
export function usePackStatus(packId: string, onSettled?: () => void) {
  const [status, setStatus] = useState<PackStatus | null>(null);
  const wasBusy = useRef(false);
  const settled = useRef(onSettled);
  settled.current = onSettled;
  const fetchStatus = useCallback(async () => {
    const s = await api<PackStatus>(`/api/packs/${packId}/status`);
    setStatus(s);
    return s;
  }, [packId]);
  useEffect(() => { if (UUID.test(packId)) fetchStatus().catch(() => undefined); }, [packId, fetchStatus]);
  const busy = isBusy(status);
  useEffect(() => {
    if (wasBusy.current && !busy) settled.current?.();
    wasBusy.current = busy;
  }, [busy]);
  usePoll(async () => isBusy(await fetchStatus()), busy);
  return { status, busy, refresh: fetchStatus };
}

// ---------- /packs ----------
export function PacksPage() {
  const { data, error, reload } = useLoad(() => api<{ packs: Pack[] }>("/api/packs"), []);
  const [title, setTitle] = useState("");
  const [buyer, setBuyer] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setProblem(null);
    let pack: Pack | null = null;
    try {
      pack = await api<Pack>("/api/packs", { method: "POST", body: { title, buyer } });
      if (file) {
        const form = new FormData();
        form.append("file", file);
        await api(`/api/packs/${pack.id}/documents`, { method: "POST", form });
      }
      navigate(`/pack?id=${pack.id}`);
    } catch (err) {
      setProblem(pack ? `The pack was created but the file was not uploaded: ${errorText(err)}` : errorText(err));
      if (pack) reload();
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <Title>Tender packs</Title>
      {error && <Alert>{error}</Alert>}
      <Card title="Your packs">
        {!data ? <p className="text-slate-600">Loading…</p> : data.packs.length === 0 ? (
          <p className="text-slate-700">No packs yet. Start one below.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {data.packs.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <Link to={`/pack?id=${p.id}`}>{p.title}</Link>
                  <p className="text-sm text-slate-600">{p.buyer || "No buyer named"}{p.deadline ? ` · deadline ${new Date(p.deadline).toLocaleDateString("en-GB")}` : ""}</p>
                </div>
                <Badge tone={p.status === "ready" || p.status === "signed" ? "green" : "slate"}>{STATUS_LABEL[p.status] ?? p.status}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Start a new pack">
        <form onSubmit={create} className="space-y-4">
          {problem && <Alert>{problem}</Alert>}
          <Field id="pack-title" label="Pack title" value={title} onChange={setTitle} required />
          <Field id="pack-buyer" label="Buyer (council)" value={buyer} onChange={setBuyer} />
          <div>
            <label htmlFor="pack-file" className="block text-sm font-medium text-slate-800">Tender document (PDF or Word, optional now)</label>
            <input id="pack-file" type="file" accept=".pdf,.docx" className="mt-1 block text-sm"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </div>
          <Button type="submit" busy={busy}>Create pack</Button>
        </form>
      </Card>
    </div>
  );
}

// ---------- /pack?id= ----------
export function PackPage() {
  const id = queryId();
  return UUID.test(id) ? <PackPageView id={id} /> : <NoId what="Tender pack" />;
}

function PackPageView({ id }: { id: string }) {
  const pack = useLoad(() => api<Pack>(`/api/packs/${id}`), [id]);
  const docs = useLoad(() => api<{ documents: Doc[] }>(`/api/packs/${id}/documents`), [id]);
  const reqs = useLoad(() => api<{ requirements: Req[] }>(`/api/packs/${id}/requirements`), [id]);
  const reloadAll = () => { pack.reload(); docs.reload(); reqs.reload(); };
  const { status, busy, refresh } = usePackStatus(id, reloadAll);
  const [problem, setProblem] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const act = async (path: string) => {
    setWorking(true);
    setProblem(null);
    try { await api(`/api/packs/${id}/${path}`, { method: "POST" }); await refresh(); } catch (err) { setProblem(errorText(err)); }
    setWorking(false);
  };
  const upload = async (file: File | undefined) => {
    if (!file) return;
    setWorking(true);
    setProblem(null);
    try {
      const form = new FormData();
      form.append("file", file);
      await api(`/api/packs/${id}/documents`, { method: "POST", form });
      docs.reload();
    } catch (err) { setProblem(errorText(err)); }
    setWorking(false);
  };

  const p = status?.pack ?? pack.data;
  const state = p?.status ?? "";
  const hasDocs = (docs.data?.documents.length ?? 0) > 0;
  const questions = (reqs.data?.requirements ?? []).filter((r) => r.kind === "question" && r.status === "confirmed");
  return (
    <div className="space-y-6">
      <Title back={{ to: "/packs", label: "All packs" }}>{p?.title ?? "Tender pack"}</Title>
      {pack.error && <Alert>{pack.error}</Alert>}
      {problem && <Alert>{problem}</Alert>}
      <ProgressLine status={status} />
      <FailedTask status={status} />
      {p && <p className="text-slate-700">{p.buyer || "No buyer named"} · <Badge tone="blue">{STATUS_LABEL[state] ?? state}</Badge></p>}

      <Card title="Tender documents">
        {docs.data && docs.data.documents.length > 0 ? (
          <ul className="mb-4 list-disc pl-5 text-slate-800">
            {docs.data.documents.map((d) => <li key={d.id}>{d.filename} <span className="text-sm text-slate-600">({d.page_count} pages)</span></li>)}
          </ul>
        ) : <p className="mb-4 text-slate-700">No tender document yet.</p>}
        {!["signed", "exported"].includes(state) && (
          <div>
            <label htmlFor="tender-file" className="block text-sm font-medium text-slate-800">Add a tender document</label>
            <input id="tender-file" type="file" accept=".pdf,.docx" className="mt-1 block text-sm" disabled={working}
              onChange={(e) => { void upload(e.target.files?.[0]); e.target.value = ""; }} />
          </div>
        )}
      </Card>

      <Card title="Next step">
        <div className="flex flex-wrap gap-3">
          {["uploaded", "extracting", "review"].includes(state) && (
            <Button busy={working} disabled={busy || !hasDocs} onClick={() => act("extract")}>Find the requirements</Button>
          )}
          <Link to={`/checklist?id=${id}`} className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-100">Review the checklist</Link>
          {["drafting", "ready"].includes(state) && (
            <>
              <Button variant="secondary" busy={working} disabled={busy} onClick={() => act("draft")}>Draft the answers</Button>
              <Button variant="secondary" busy={working} disabled={busy} onClick={() => act("check")}>Check the claims</Button>
            </>
          )}
          <Link to={`/coverage?id=${id}`} className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-100">Coverage and sign-off</Link>
        </div>
        {!hasDocs && ["uploaded"].includes(state) && <p className="mt-3 text-sm text-slate-600">Upload the tender document to start.</p>}
      </Card>

      {questions.length > 0 && (
        <Card title="Questions">
          <ol className="space-y-2">
            {questions.map((r) => (
              <li key={r.id} className="flex items-start justify-between gap-3">
                <span className="text-slate-800"><strong>{r.ref || `Q${r.seq}`}</strong> {r.text.slice(0, 160)}{r.text.length > 160 ? "…" : ""}</span>
                <Link to={`/draft?id=${r.id}`}>Open answer</Link>
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}

// ---------- /checklist?id= ----------
const KINDS = ["question", "mandatory", "deadline", "other"];
const FLAG_TEXT: Record<string, string> = {
  quote_unverified: "The quote could not be found in the document", limit_unverified: "Check the limit",
  limit_conflict: "Limits disagree", duplicate: "Possible duplicate", low_confidence: "Low confidence",
};
const flagText = (f: string) => FLAG_TEXT[f] ?? f.replace(/_/g, " ");

function ReqRow({ r, locked, onChanged }: { r: Req; locked: boolean; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(r.text);
  const [kind, setKind] = useState(r.kind);
  const [limit, setLimit] = useState(r.word_limit?.toString() ?? "");
  const [problem, setProblem] = useState<string | null>(null);
  const patch = async (body: Record<string, unknown>) => {
    setProblem(null);
    try { await api(`/api/requirements/${r.id}`, { method: "PATCH", body }); setEditing(false); onChanged(); } catch (err) { setProblem(errorText(err)); }
  };
  return (
    <li className="rounded-md border border-slate-200 bg-white p-4" data-testid={`req-${r.seq}`}>
      <div className="flex flex-wrap items-center gap-2">
        <strong>{r.ref || `#${r.seq}`}</strong>
        <Badge tone="slate">{r.kind}</Badge>
        <Badge tone={r.status === "confirmed" ? "green" : "blue"}>{r.status}</Badge>
        {r.origin === "user" && <Badge tone="slate">added by you</Badge>}
        {r.edited && r.origin !== "user" && <Badge tone="slate">edited</Badge>}
        {r.word_limit && <span className="text-sm text-slate-600">{r.word_limit} words</span>}
        {r.marks != null && <span className="text-sm text-slate-600">{r.marks} marks</span>}
        {r.flags.map((f) => <Badge key={f} tone="amber">{flagText(f)}</Badge>)}
        {r.origin === "model" && !r.quote_verified && !r.flags.includes("quote_unverified") && <Badge tone="amber">Quote not verified</Badge>}
      </div>
      {editing ? (
        <div className="mt-3 space-y-3">
          <Field id={`t-${r.id}`} label="Requirement text" value={text} onChange={setText} multiline />
          <div className="flex gap-4">
            <div>
              <label htmlFor={`k-${r.id}`} className="block text-sm font-medium text-slate-800">Type</label>
              <select id={`k-${r.id}`} value={kind} onChange={(e) => setKind(e.target.value)} className="mt-1 rounded-md border border-slate-300 px-2 py-2">
                {KINDS.map((k) => <option key={k}>{k}</option>)}
              </select>
            </div>
            <Field id={`l-${r.id}`} label="Word limit" value={limit} onChange={setLimit} />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => patch({ text, kind, word_limit: limit.trim() ? Number(limit) : null })}>Save</Button>
            <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
          </div>
        </div>
      ) : (
        <>
          <p className="mt-2 whitespace-pre-wrap text-slate-900">{r.text}</p>
          {r.source_quote && <blockquote className="mt-2 border-l-4 border-slate-300 pl-3 text-sm text-slate-600">{r.source_quote}{r.source_page ? ` (page ${r.source_page})` : ""}</blockquote>}
        </>
      )}
      {problem && <div className="mt-2"><Alert>{problem}</Alert></div>}
      {!editing && !locked && (
        <div className="mt-3 flex flex-wrap gap-2">
          {r.status !== "confirmed" && <Button variant="secondary" onClick={() => patch({ status: "confirmed" })}>Confirm</Button>}
          <Button variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
          <Button variant="secondary" onClick={() => patch({ status: "removed" })}>Remove</Button>
        </div>
      )}
    </li>
  );
}

export function ChecklistPage() {
  const id = queryId();
  return UUID.test(id) ? <ChecklistPageView id={id} /> : <NoId what="Checklist" />;
}

function ChecklistPageView({ id }: { id: string }) {
  const list = useLoad(() => api<{ requirements: Req[] }>(`/api/packs/${id}/requirements`), [id]);
  const { status, refresh } = usePackStatus(id, () => list.reload());
  const [text, setText] = useState("");
  const [kind, setKind] = useState("question");
  const [limit, setLimit] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<string | null>(null);
  const locked = ["signed", "exported"].includes(status?.pack.status ?? "");
  const rows = list.data?.requirements ?? [];

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setProblem(null);
    try {
      await api(`/api/packs/${id}/requirements`, { method: "POST", body: { text, kind, word_limit: limit.trim() ? Number(limit) : null } });
      setText(""); setLimit("");
      list.reload();
    } catch (err) { setProblem(errorText(err)); }
  };
  const confirmAll = async () => {
    setProblem(null);
    try {
      const res = await api<{ confirmed: number }>(`/api/packs/${id}/confirm`, { method: "POST" });
      setConfirmed(`Checklist confirmed (${res.confirmed} item${res.confirmed === 1 ? "" : "s"} newly confirmed). You can draft answers now.`);
      list.reload();
      await refresh();
    } catch (err) { setProblem(errorText(err)); }
  };
  const flagged = rows.filter((r) => r.flags.length > 0).length;

  return (
    <div className="space-y-6">
      <Title back={{ to: `/pack?id=${id}`, label: "Back to the pack" }}>Checklist</Title>
      <ProgressLine status={status} />
      {list.error && <Alert>{list.error}</Alert>}
      {problem && <Alert>{problem}</Alert>}
      {confirmed && <Alert kind="success">{confirmed}</Alert>}
      {flagged > 0 && <Alert kind="info">{flagged} item{flagged === 1 ? " has" : "s have"} an amber flag. Check those against the tender document before you confirm.</Alert>}
      {!list.data ? <p className="text-slate-600">Loading…</p> : rows.length === 0 ? (
        <p className="text-slate-700">No requirements yet. Run the extraction from the pack page, or add them by hand below.</p>
      ) : (
        <ul className="space-y-3">{rows.map((r) => <ReqRow key={`${r.id}-${r.status}-${r.text}`} r={r} locked={locked} onChanged={list.reload} />)}</ul>
      )}
      {!locked && rows.length > 0 && <Button onClick={confirmAll}>Confirm the checklist</Button>}
      {!locked && (
        <Card title="Add a requirement">
          <form onSubmit={add} className="space-y-3">
            <Field id="new-text" label="Requirement text" value={text} onChange={setText} multiline required />
            <div className="flex gap-4">
              <div>
                <label htmlFor="new-kind" className="block text-sm font-medium text-slate-800">Type</label>
                <select id="new-kind" value={kind} onChange={(e) => setKind(e.target.value)} className="mt-1 rounded-md border border-slate-300 px-2 py-2">
                  {KINDS.map((k) => <option key={k}>{k}</option>)}
                </select>
              </div>
              <Field id="new-limit" label="Word limit" value={limit} onChange={setLimit} />
            </div>
            <Button type="submit">Add requirement</Button>
          </form>
        </Card>
      )}
    </div>
  );
}

// ---------- /evidence ----------
const CATEGORY_LABEL: Record<string, string> = {
  policy: "Policy", case_study: "Case study", accreditation: "Accreditation", social_value: "Social value", company_facts: "Company facts", past_bid: "Past bid",
};

export function EvidencePage() {
  const { data, error, reload } = useLoad(() => api<{ documents: Doc[] }>("/api/evidence/documents"), []);
  const [category, setCategory] = useState("policy");
  const [problem, setProblem] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);

  const upload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem("evidence-file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) { setProblem("Choose a file first."); return; }
    setWorking(true); setProblem(null); setNotice(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("category", category);
      const res = await api<{ passages: number }>("/api/evidence/documents", { method: "POST", form });
      setNotice(`Added: ${res.passages} passage${res.passages === 1 ? "" : "s"} are now available to cite.`);
      input.value = "";
      reload();
    } catch (err) { setProblem(errorText(err)); }
    setWorking(false);
  };
  const remove = async (id: string) => {
    setProblem(null); setNotice(null);
    try {
      await api(`/api/documents/${id}`, { method: "DELETE" });
      setConfirming(null);
      setNotice("Removed. Answers that cited it need checking again.");
      reload();
    } catch (err) { setProblem(errorText(err)); }
  };

  return (
    <div className="space-y-6">
      <Title>Evidence library</Title>
      <p className="text-slate-700">Your own policies, case studies and accreditations. Drafts may only cite what is here.</p>
      {error && <Alert>{error}</Alert>}
      {problem && <Alert>{problem}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      <Card title="Add evidence">
        <form onSubmit={upload} className="space-y-4">
          <div>
            <label htmlFor="evidence-file" className="block text-sm font-medium text-slate-800">File (PDF, Word or text)</label>
            <input id="evidence-file" name="evidence-file" type="file" accept=".pdf,.docx,.txt" className="mt-1 block text-sm" />
          </div>
          <div>
            <label htmlFor="evidence-category" className="block text-sm font-medium text-slate-800">Category</label>
            <select id="evidence-category" value={category} onChange={(e) => setCategory(e.target.value)} className="mt-1 rounded-md border border-slate-300 px-2 py-2">
              {Object.entries(CATEGORY_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <Button type="submit" busy={working}>Upload</Button>
        </form>
      </Card>
      <Card title="In your library">
        {!data ? <p className="text-slate-600">Loading…</p> : data.documents.length === 0 ? <p className="text-slate-700">Nothing here yet.</p> : (
          <ul className="divide-y divide-slate-200">
            {data.documents.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <span>{d.filename} <Badge tone="slate">{CATEGORY_LABEL[d.category ?? ""] ?? d.category ?? "Other"}</Badge> <span className="text-sm text-slate-600">{d.page_count} page{d.page_count === 1 ? "" : "s"}</span></span>
                {confirming === d.id ? (
                  <span className="flex items-center gap-2 text-sm">
                    Remove it? Answers that cite it will need checking again.
                    <Button variant="danger" onClick={() => remove(d.id)}>Yes, remove</Button>
                    <Button variant="secondary" onClick={() => setConfirming(null)}>Keep</Button>
                  </span>
                ) : <Button variant="secondary" onClick={() => setConfirming(d.id)} aria-label={`Remove ${d.filename}`}>Remove</Button>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

// ---------- /draft?id= (id is the question) ----------
const VERDICT: Record<string, { label: string; tone: "green" | "red" | "amber" }> = {
  supported: { label: "Supported", tone: "green" }, unsupported: { label: "Unsupported", tone: "red" },
  contradicted: { label: "Contradicted", tone: "red" }, unchecked: { label: "Not checked", tone: "amber" },
};
const verdictOf = (v: string) => VERDICT[v] ?? { label: v, tone: "amber" as const };

/** The answer with [E-n] markers shown as chips and every non-supported claim span marked. */
export function AnswerText({ text, claims }: { text: string; claims: Claim[] }) {
  const marks: { a: number; b: number; tone: string }[] = [];
  for (const c of claims) {
    if (c.verdict === "supported" || !c.span) continue;
    const a = text.indexOf(c.span);
    if (a >= 0 && !marks.some((m) => a < m.b && a + c.span.length > m.a)) marks.push({ a, b: a + c.span.length, tone: c.verdict });
  }
  marks.sort((x, y) => x.a - y.a);
  const parts: ReactNode[] = [];
  const chips = (s: string, key: string) => s.split(/(\[E-\d+\])/).map((piece, i) =>
    /^\[E-\d+\]$/.test(piece) ? <span key={`${key}-${i}`} className="rounded bg-blue-100 px-1 text-xs font-semibold text-blue-900">{piece}</span> : piece);
  let at = 0;
  marks.forEach((m, i) => {
    if (m.a > at) parts.push(<span key={`p${i}`}>{chips(text.slice(at, m.a), `p${i}`)}</span>);
    parts.push(<mark key={`m${i}`} data-verdict={m.tone} className={m.tone === "unchecked" ? "bg-amber-200" : "bg-red-200"}>{chips(text.slice(m.a, m.b), `m${i}`)}</mark>);
    at = m.b;
  });
  parts.push(<span key="end">{chips(text.slice(at), "end")}</span>);
  return <p className="whitespace-pre-wrap leading-relaxed text-slate-900">{parts}</p>;
}

type DraftReply = { requirement: Req; draft: Draft | null; versions: { version: number; author: string; word_count: number }[] };

export function DraftPage() {
  const id = queryId();
  return UUID.test(id) ? <DraftPageView id={id} /> : <NoId what="Answer" />;
}

function DraftPageView({ id }: { id: string }) {
  const data = useLoad(() => api<DraftReply>(`/api/requirements/${id}/draft`), [id]);
  const claims = useLoad(() => api<{ draft_version: number | null; checked: boolean; claims: Claim[] }>(`/api/requirements/${id}/claims`), [id]);
  const citedKey = (data.data?.draft?.cited_ids ?? []).join(",");
  const passages = useLoad(() => citedKey ? api<{ passages: Passage[] }>(`/api/evidence/passages?ids=${citedKey}`) : Promise.resolve({ passages: [] }), [citedKey]);
  const packId = data.data?.requirement.pack_id ?? "";
  const { status, busy, refresh } = usePackStatus(packId, () => { data.reload(); claims.reload(); });
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const d = data.data?.draft ?? null;
  const req = data.data?.requirement;
  const locked = ["signed", "exported"].includes(status?.pack.status ?? "");
  const act = async (fn: () => Promise<unknown>) => {
    setWorking(true); setProblem(null);
    try { await fn(); } catch (err) { setProblem(errorText(err)); }
    setWorking(false);
  };
  const save = () => act(async () => {
    await api(`/api/requirements/${id}/draft`, { method: "PUT", body: { text, base_version: d?.version ?? 0 } });
    setEditing(false); data.reload(); claims.reload();
  });
  const redraft = () => act(async () => { await api(`/api/requirements/${id}/redraft`, { method: "POST" }); await refresh(); });
  const check = () => act(async () => { await api(`/api/packs/${packId}/check`, { method: "POST" }); await refresh(); });
  const overLimit = !!d && d.word_limit != null && d.word_count > d.word_limit;
  const unresolved = (claims.data?.claims ?? []).filter((c) => c.verdict !== "supported").length;

  return (
    <div className="space-y-6">
      <Title back={packId ? { to: `/pack?id=${packId}`, label: "Back to the pack" } : undefined}>{req ? `${req.ref || `Question ${req.seq}`}` : "Answer"}</Title>
      {data.error && <Alert>{data.error}</Alert>}
      {problem && <Alert>{problem}</Alert>}
      <ProgressLine status={status} />
      {req && <Card><p className="whitespace-pre-wrap text-slate-900">{req.text}</p></Card>}
      {data.data && !d && <Alert kind="info">No answer has been drafted yet. Use "Draft the answers" on the pack page.</Alert>}
      {d && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title={`Draft (version ${d.version}, ${d.author === "ai" ? "AI" : "edited by you"})`}>
            {editing ? (
              <div className="space-y-3">
                <Field id="draft-text" label="Answer" value={text} onChange={setText} multiline />
                <div className="flex gap-2">
                  <Button busy={working} onClick={save}>Save as a new version</Button>
                  <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
                </div>
              </div>
            ) : <AnswerText text={d.text} claims={claims.data?.claims ?? []} />}
            <p className="mt-3 text-sm text-slate-600">
              {d.word_count} word{d.word_count === 1 ? "" : "s"}{d.word_limit ? ` of ${d.word_limit}` : ""}
              {overLimit && <> <Badge tone="red">Over the limit</Badge></>}
              {d.gap_count > 0 && <> <Badge tone="amber">{d.gap_count} gap{d.gap_count === 1 ? "" : "s"} to fill</Badge></>}
              {d.outside_ids.length > 0 && <> <Badge tone="amber">Cites evidence that was not retrieved</Badge></>}
            </p>
            {!editing && !locked && (
              <div className="mt-3 flex flex-wrap gap-2">
                <Button variant="secondary" onClick={() => { setText(d.text); setEditing(true); }}>Edit</Button>
                <Button variant="secondary" busy={working} disabled={busy} onClick={redraft}>Redraft</Button>
                <Button variant="secondary" busy={working} disabled={busy} onClick={check}>Check the claims</Button>
              </div>
            )}
          </Card>
          <Card title="Source passages">
            {!passages.data ? <p className="text-slate-600">Loading…</p> : passages.data.passages.length === 0 ? (
              <p className="text-slate-700">This answer cites no evidence.</p>
            ) : (
              <ul className="space-y-4">
                {passages.data.passages.map((p) => (
                  <li key={p.display_no} data-testid={`passage-${p.display_no}`}>
                    <p className="text-sm font-semibold text-slate-800">{p.label} · {p.document}, page {p.page_from}{p.page_to !== p.page_from ? `-${p.page_to}` : ""}</p>
                    {p.removed ? <Alert>This evidence was removed. Re-check this answer after you fix the citation.</Alert>
                      : <blockquote className="mt-1 border-l-4 border-blue-200 pl-3 text-sm text-slate-800">{p.text}</blockquote>}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
      {d && (
        <Card title="Claims">
          {claims.data && !claims.data.checked && <div className="mb-3"><Alert kind="info">This version has not been checked yet. The table may be out of date.</Alert></div>}
          {unresolved > 0 && <div className="mb-3"><Alert>{unresolved} claim{unresolved === 1 ? " is" : "s are"} not supported by your evidence. Edit the sentence or remove it.</Alert></div>}
          {!claims.data || claims.data.claims.length === 0 ? <p className="text-slate-700">No claims recorded.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead><tr className="border-b border-slate-300"><th className="py-2 pr-3">Claim</th><th className="pr-3">Verdict</th><th className="pr-3">Evidence</th><th>Why</th></tr></thead>
                <tbody>
                  {claims.data.claims.map((c) => {
                    const v = verdictOf(c.verdict);
                    return (
                      <tr key={c.seq} data-verdict={c.verdict} className={`border-b border-slate-200 align-top ${c.verdict === "supported" ? "" : c.verdict === "unchecked" ? "bg-amber-50" : "bg-red-50"}`}>
                        <td className="py-2 pr-3">{c.span}</td>
                        <td className="pr-3"><Badge tone={v.tone}>{v.label}</Badge></td>
                        <td className="pr-3">{c.cited_ids.map((n) => `E-${n}`).join(", ")}{c.evidence_quote && <q className="block text-slate-600">{c.evidence_quote}</q>}</td>
                        <td>{c.reason}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

// ---------- /coverage?id= ----------
export type CoverageRow = {
  requirement_id: string; seq: number; ref: string; kind: string; text: string; answered: boolean | null; words: number | null;
  word_limit: number | null; within_limit: boolean | null; gaps: number; checked: boolean; claims: Record<string, number>; covered: boolean;
};
export type Coverage = {
  pack: Pack; rows: CoverageRow[]; export: { allowed: boolean; reasons: string[] }; statement: { version: string; text: string };
  signoff: { reviewer_name: string; signed_at: string } | null; notice: string;
};
const reasonText = (r: string) => r.split(": ").slice(1).join(": ") || r;
const reasonCode = (r: string) => r.split(":", 1)[0];

export function CoveragePage() {
  const id = queryId();
  return UUID.test(id) ? <CoveragePageView id={id} /> : <NoId what="Coverage" />;
}

function CoveragePageView({ id }: { id: string }) {
  const cov = useLoad(() => api<Coverage>(`/api/packs/${id}/coverage`), [id]);
  usePackStatus(id, () => cov.reload());
  const [name, setName] = useState("");
  const [ticked, setTicked] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const c = cov.data;
  const blockers = (c?.export.reasons ?? []).filter((r) => reasonCode(r) !== "no_signoff");
  const signed = !!c && ["signed", "exported"].includes(c.pack.status) && !!c.signoff;
  const canSign = !!c && c.pack.status === "ready" && blockers.length === 0;

  const sign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!c) return;
    setWorking(true); setProblem(null);
    try {
      await api(`/api/packs/${id}/signoff`, { method: "POST", body: { reviewer_name: name, accept_statement: ticked, statement_version: c.statement.version } });
      cov.reload();
    } catch (err) { setProblem(errorText(err)); }
    setWorking(false);
  };

  return (
    <div className="space-y-6">
      <Title back={{ to: `/pack?id=${id}`, label: "Back to the pack" }}>Coverage and sign-off</Title>
      {cov.error && <Alert>{cov.error}</Alert>}
      {c && <Alert kind="info">{c.notice}</Alert>}
      {c && (
        <Card title="What is answered">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-slate-300"><th className="py-2 pr-3">Item</th><th className="pr-3">Answered</th><th className="pr-3">Words</th><th className="pr-3">Gaps</th><th className="pr-3">Claims</th><th>Checked</th></tr></thead>
              <tbody>
                {c.rows.map((r) => (
                  <tr key={r.requirement_id} className="border-b border-slate-200 align-top" data-testid={`cov-${r.seq}`}>
                    <td className="py-2 pr-3">
                      {r.kind === "question" ? <Link to={`/draft?id=${r.requirement_id}`}>{r.ref || `Q${r.seq}`}</Link> : <strong>{r.ref || `#${r.seq}`}</strong>}
                      <span className="block text-slate-600">{r.text.slice(0, 90)}{r.text.length > 90 ? "…" : ""}</span>
                    </td>
                    <td className="pr-3">{r.answered === null ? (r.covered ? "Confirmed" : "-") : r.answered ? "Yes" : <Badge tone="amber">No</Badge>}</td>
                    <td className="pr-3">{r.words == null ? "-" : r.word_limit ? <>{r.words} / {r.word_limit} {r.within_limit === false && <Badge tone="red">Over</Badge>}</> : r.words}</td>
                    <td className="pr-3">{r.gaps > 0 ? <Badge tone="amber">{r.gaps}</Badge> : 0}</td>
                    <td className="pr-3">{Object.keys(r.claims).length === 0 ? "-" : Object.entries(r.claims).map(([v, n]) => <span key={v} className="mr-1"><Badge tone={verdictOf(v).tone}>{n} {verdictOf(v).label.toLowerCase()}</Badge></span>)}</td>
                    <td>{r.kind !== "question" ? "-" : r.checked ? "Yes" : <Badge tone="amber">No</Badge>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {c && (
        <Card title="Sign-off">
          {signed && c.signoff ? (
            <Alert kind="success">Signed off by {c.signoff.reviewer_name} on {new Date(c.signoff.signed_at).toLocaleDateString("en-GB")}. Any change to an answer or the checklist means signing off again.</Alert>
          ) : (
            <form onSubmit={sign} className="space-y-4">
              {blockers.length > 0 && (
                <div role="status" className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  <p className="font-semibold">Sign-off is not possible yet:</p>
                  <ul className="list-disc pl-5">{blockers.map((r) => <li key={r}>{reasonText(r)}</li>)}</ul>
                </div>
              )}
              {problem && <Alert>{problem}</Alert>}
              <blockquote className="rounded-md border border-slate-300 bg-slate-50 p-4 text-slate-900" aria-label="Responsibility statement">{c.statement.text}</blockquote>
              <label className="flex items-start gap-2 text-sm text-slate-900">
                <input type="checkbox" checked={ticked} onChange={(e) => setTicked(e.target.checked)} className="mt-1" />
                I have read this statement and I accept it for my firm.
              </label>
              <Field id="reviewer" label="Your full name" value={name} onChange={setName} required autoComplete="name" />
              <Button type="submit" busy={working} disabled={!canSign || !ticked || !name.trim()}>Sign off this pack</Button>
            </form>
          )}
        </Card>
      )}
    </div>
  );
}
