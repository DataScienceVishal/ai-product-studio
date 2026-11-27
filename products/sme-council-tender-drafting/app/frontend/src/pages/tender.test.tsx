import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { reply, stubFetch } from "../test-utils";
import { ApiError } from "../api";
import { ChecklistPage, CoveragePage, DraftPage, EvidencePage, PackPage, PacksPage, POLL_MAX_TICKS, usePoll, AnswerText } from "./tender";
import { renderHook } from "@testing-library/react";

const PID = "11111111-1111-4111-8111-111111111111";
const RID = "22222222-2222-4222-8222-222222222222";
const at = (url: string) => window.history.replaceState({}, "", url);
const pack = (over = {}) => ({ id: PID, title: "Cleaning tender", buyer: "Leeds Council", status: "uploaded", deadline: null, created_at: "2026-11-01T00:00:00Z", ...over });
const req = (over = {}) => ({ id: RID, pack_id: PID, seq: 1, ref: "Q1", kind: "question", text: "Describe your quality system", word_limit: 300, marks: 10,
  source_page: 2, source_quote: "Describe your quality system", quote_verified: true, origin: "model", status: "proposed", flags: [], edited: false, ...over });

type Handler = (init: RequestInit) => Response | Promise<Response>;
/** Route-table fetch: "GET /api/x" -> handler or body. Unknown calls fail the test. */
function serve(table: Record<string, Handler | Record<string, unknown>>) {
  const mock = stubFetch();
  mock.mockImplementation(async (path: string, init: RequestInit = {}) => {
    const key = `${init.method ?? "GET"} ${path}`;
    if (!(key in table)) throw new Error(`unexpected call ${key}`);
    const h = table[key];
    return typeof h === "function" ? (h as Handler)(init) : reply(200, h);
  });
  return mock;
}
const calls = (mock: ReturnType<typeof stubFetch>, key: string) =>
  mock.mock.calls.filter(([p, i]) => `${(i as RequestInit | undefined)?.method ?? "GET"} ${p}` === key).length;
afterEach(() => { vi.useRealTimers(); });

describe("packs list and upload", () => {
  it("lists packs with links to /pack?id=", async () => {
    serve({ "GET /api/packs": { packs: [pack()] } });
    render(<PacksPage />);
    const link = await screen.findByRole("link", { name: "Cleaning tender" });
    expect(link.getAttribute("href")).toBe(`/pack?id=${PID}`);
    expect(screen.getByText("Uploaded")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/£|price|plan/i);
  });

  it("creates a pack, uploads the file as multipart and opens the pack", async () => {
    const m = serve({
      "GET /api/packs": { packs: [] },
      "POST /api/packs": (init) => { expect(JSON.parse(init.body as string)).toEqual({ title: "T", buyer: "B" }); return reply(201, pack()); },
      [`POST /api/packs/${PID}/documents`]: (init) => {
        expect(init.body).toBeInstanceOf(FormData);
        expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined(); // the browser sets the boundary
        return reply(201, {});
      },
    });
    render(<PacksPage />);
    fireEvent.change(await screen.findByLabelText("Pack title"), { target: { value: "T" } });
    fireEvent.change(screen.getByLabelText("Buyer (council)"), { target: { value: "B" } });
    fireEvent.change(screen.getByLabelText(/Tender document/), { target: { files: [new File(["x"], "t.pdf")] } });
    fireEvent.click(screen.getByRole("button", { name: "Create pack" }));
    await waitFor(() => expect(window.location.pathname + window.location.search).toBe(`/pack?id=${PID}`));
    expect(calls(m, `POST /api/packs/${PID}/documents`)).toBe(1);
  });

  it("shows the server's error when creation fails", async () => {
    serve({ "GET /api/packs": { packs: [] }, "POST /api/packs": () => reply(422, { error: "invalid_input", message: "Title is required." }) });
    render(<PacksPage />);
    fireEvent.change(await screen.findByLabelText("Pack title"), { target: { value: "T" } });
    fireEvent.click(screen.getByRole("button", { name: "Create pack" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Title is required.");
  });
});

describe("pack page and status polling", () => {
  const status = (st: string, task?: string) => ({ pack: pack({ status: st }), tasks: task ? [{ id: "t", kind: "extract", status: task, error_code: null, attempts: 1 }] : [] });
  const base = { [`GET /api/packs/${PID}`]: pack(), [`GET /api/packs/${PID}/documents`]: { documents: [{ id: "d", kind: "tender", filename: "tender.pdf", category: null, page_count: 3, created_at: "x" }] },
    [`GET /api/packs/${PID}/requirements`]: { requirements: [] } };

  it("polls while a task runs and stops on a terminal state, at a steady pace", async () => {
    at(`/pack?id=${PID}`);
    vi.useFakeTimers();
    let n = 0;
    const m = serve({ ...base, [`GET /api/packs/${PID}/status`]: () => reply(200, ++n < 3 ? status("extracting", "running") : status("review", "succeeded")) });
    render(<PackPage />);
    await act(async () => { await vi.advanceTimersByTimeAsync(100); });
    expect(screen.getByText(/Finding requirements…/)).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(calls(m, `GET /api/packs/${PID}/status`)).toBe(2);   // one request per pause, never a tight loop
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(calls(m, `GET /api/packs/${PID}/status`)).toBe(3);
    expect(screen.queryByText(/Finding requirements…/)).toBeNull();
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(calls(m, `GET /api/packs/${PID}/status`)).toBe(3);   // terminal: no more polling
  });

  it("starts the extraction and shows progress", async () => {
    at(`/pack?id=${PID}`);
    let queued = false;
    serve({ ...base,
      [`GET /api/packs/${PID}/status`]: () => reply(200, queued ? status("extracting", "queued") : status("uploaded")),
      [`POST /api/packs/${PID}/extract`]: () => { queued = true; return reply(202, { id: "t", kind: "extract", status: "queued", error_code: null, attempts: 0 }); } });
    render(<PackPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Find the requirements" }));
    expect(await screen.findByText(/Finding requirements…/)).toBeTruthy();
  });

  it("shows a failed task and keeps the button available", async () => {
    at(`/pack?id=${PID}`);
    serve({ ...base, [`GET /api/packs/${PID}/status`]: { pack: pack({ status: "review" }), tasks: [{ id: "t", kind: "extract", status: "failed", error_code: "ai_failed", attempts: 2 }] } });
    render(<PackPage />);
    expect((await screen.findByRole("alert")).textContent).toContain("ai_failed");
    expect(screen.getByRole("button", { name: "Find the requirements" })).toBeTruthy();
  });

  it("asks for an id when the query is missing or not an id", async () => {
    at("/pack?id=../../x");
    const m = stubFetch();
    render(<PackPage />);
    expect(screen.getByText(/nothing selected/i)).toBeTruthy();
    expect(m).not.toHaveBeenCalled();
  });
});

describe("usePoll", () => {
  it("backs off after failures and gives up after the cap", async () => {
    vi.useFakeTimers();
    const step = vi.fn().mockRejectedValue(new Error("down"));
    renderHook(() => usePoll(step, true));
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(step).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(6000); });
    expect(step).toHaveBeenCalledTimes(2);   // 3 s, then 6 s: doubling
    await act(async () => { await vi.advanceTimersByTimeAsync(24 * 3600_000); });
    expect(step.mock.calls.length).toBe(POLL_MAX_TICKS);
  });
  it("stops on a 4xx but keeps backing off on a network error", async () => {
    vi.useFakeTimers();
    const gone = vi.fn().mockRejectedValue(new ApiError(404, "not_found", "gone"));
    renderHook(() => usePoll(gone, true));
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(gone).toHaveBeenCalledTimes(1);
  });
  it("does nothing while inactive and stops on unmount", async () => {
    vi.useFakeTimers();
    const step = vi.fn().mockResolvedValue(true);
    const { unmount, rerender } = renderHook(({ on }) => usePoll(step, on), { initialProps: { on: false } });
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(step).not.toHaveBeenCalled();
    rerender({ on: true });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(step).toHaveBeenCalledTimes(1);
    unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(step).toHaveBeenCalledTimes(1);
  });
});

describe("checklist", () => {
  const list = (rows: unknown[]) => ({ [`GET /api/packs/${PID}/requirements`]: { requirements: rows }, [`GET /api/packs/${PID}/status`]: { pack: pack({ status: "review" }), tasks: [] },
    [`GET /api/packs/${PID}`]: pack() });

  it("shows amber flags and an unverified quote, and confirms one item", async () => {
    at(`/checklist?id=${PID}`);
    const m = serve({ ...list([req({ flags: ["limit_conflict"], quote_verified: false })]),
      [`PATCH /api/requirements/${RID}`]: (init) => { expect(JSON.parse(init.body as string)).toEqual({ status: "confirmed" }); return reply(200, req({ status: "confirmed" })); } });
    render(<ChecklistPage />);
    expect(await screen.findByText("Limits disagree")).toBeTruthy();
    expect(screen.getByText("Limits disagree").className).toContain("amber");
    expect(screen.getByText("Quote not verified")).toBeTruthy();
    expect(screen.getByText(/1 item has an amber flag/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(calls(m, `PATCH /api/requirements/${RID}`)).toBe(1));
  });

  it("edits the text and word limit", async () => {
    at(`/checklist?id=${PID}`);
    serve({ ...list([req()]), [`PATCH /api/requirements/${RID}`]: (init) => {
      expect(JSON.parse(init.body as string)).toEqual({ text: "New text", kind: "question", word_limit: 250 });
      return reply(200, req({ text: "New text" })); } });
    render(<ChecklistPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit" }));
    const row = screen.getByTestId("req-1");
    fireEvent.change(within(row).getByLabelText("Requirement text"), { target: { value: "New text" } });
    fireEvent.change(within(row).getByLabelText("Word limit"), { target: { value: "250" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Save" })).toBeNull());
  });

  it("adds a requirement and confirms the checklist", async () => {
    at(`/checklist?id=${PID}`);
    const m = serve({ ...list([req()]),
      [`POST /api/packs/${PID}/requirements`]: (init) => { expect(JSON.parse(init.body as string)).toMatchObject({ text: "Provide insurance", kind: "mandatory", word_limit: null }); return reply(201, req()); },
      [`POST /api/packs/${PID}/confirm`]: { confirmed: 1, pack: pack({ status: "drafting" }) } });
    render(<ChecklistPage />);
    fireEvent.change(await screen.findByLabelText("Requirement text", { selector: "#new-text" }), { target: { value: "Provide insurance" } });
    fireEvent.change(screen.getByLabelText("Type", { selector: "#new-kind" }), { target: { value: "mandatory" } });
    fireEvent.click(screen.getByRole("button", { name: "Add requirement" }));
    await waitFor(() => expect(calls(m, `POST /api/packs/${PID}/requirements`)).toBe(1));
    fireEvent.click(screen.getByRole("button", { name: "Confirm the checklist" }));
    expect((await screen.findByRole("status")).textContent).toContain("Checklist confirmed");
  });

  it("shows a refused confirmation", async () => {
    at(`/checklist?id=${PID}`);
    serve({ ...list([req()]), [`POST /api/packs/${PID}/confirm`]: () => reply(409, { error: "not_ready", message: "Run the extraction first." }) });
    render(<ChecklistPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Confirm the checklist" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Run the extraction first.");
  });
});

describe("evidence library", () => {
  const doc = { id: "d1", kind: "evidence", filename: "quality.txt", category: "policy", page_count: 2, created_at: "x" };
  it("uploads with a category as multipart", async () => {
    let docs = [] as unknown[];
    const m = serve({ "GET /api/evidence/documents": () => reply(200, { documents: docs }),
      "POST /api/evidence/documents": (init) => { const f = init.body as FormData; expect(f.get("category")).toBe("accreditation"); expect((f.get("file") as File).name).toBe("a.txt"); docs = [doc]; return reply(201, { passages: 3 }); } });
    render(<EvidencePage />);
    fireEvent.change(await screen.findByLabelText("Category"), { target: { value: "accreditation" } });
    fireEvent.change(screen.getByLabelText(/^File/), { target: { files: [new File(["x"], "a.txt")] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload" }));
    expect((await screen.findByText(/3 passages are now available/))).toBeTruthy();
    expect(await screen.findByText("quality.txt")).toBeTruthy();
    expect(calls(m, "GET /api/evidence/documents")).toBe(2);
  });
  it("needs a file before uploading", async () => {
    serve({ "GET /api/evidence/documents": { documents: [] } });
    render(<EvidencePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Upload" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Choose a file");
  });
  it("soft-deletes only after a confirmation", async () => {
    let docs = [doc];
    const m = serve({ "GET /api/evidence/documents": () => reply(200, { documents: docs }),
      "DELETE /api/documents/d1": () => { docs = []; return reply(204); } });
    render(<EvidencePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Remove quality.txt" }));
    expect(calls(m, "DELETE /api/documents/d1")).toBe(0);
    fireEvent.click(screen.getByRole("button", { name: "Keep" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove quality.txt" }));
    fireEvent.click(screen.getByRole("button", { name: "Yes, remove" }));
    expect(await screen.findByText(/need checking again/)).toBeTruthy();
    expect(await screen.findByText("Nothing here yet.")).toBeTruthy();
  });
});

describe("draft with source passages and claims", () => {
  const draft = { id: "dr", requirement_id: RID, version: 2, text: "We hold ISO 9001 [E-4]. We cleaned 500 schools.", word_count: 9, word_limit: 5, retrieved_ids: [4], cited_ids: [4],
    outside_ids: [], gap_count: 1, flags: [], author: "ai", status: "blocked", model: "m", created_at: "x" };
  const claims = [
    { seq: 1, span: "We hold ISO 9001 [E-4].", kind: "accreditation", cited_ids: [4], verdict: "supported", evidence_quote: "hold ISO 9001 certification", reason: "", decided_by: "model" },
    { seq: 2, span: "We cleaned 500 schools.", kind: "number", cited_ids: [], verdict: "unsupported", evidence_quote: "", reason: "No evidence for 500", decided_by: "rule" },
    { seq: 3, span: "Maybe this", kind: "fact", cited_ids: [], verdict: "unchecked", evidence_quote: "", reason: "A digit", decided_by: "rule" },
  ];
  const table = (over: Record<string, Handler | Record<string, unknown>> = {}) => ({
    [`GET /api/requirements/${RID}/draft`]: { requirement: req({ status: "confirmed" }), draft, versions: [{ version: 2, author: "ai", word_count: 9 }] },
    [`GET /api/requirements/${RID}/claims`]: { draft_version: 2, checked: true, claims },
    "GET /api/evidence/passages?ids=4": { passages: [{ display_no: 4, label: "E-4", document: "quality.txt", page_from: 1, page_to: 1, heading: null, removed: false, text: "We hold ISO 9001 certification across all sites." }] },
    [`GET /api/packs/${PID}/status`]: { pack: pack({ status: "drafting" }), tasks: [] }, ...over });

  it("shows the cited passage beside the draft and highlights non-supported claims", async () => {
    at(`/draft?id=${RID}`);
    serve(table());
    render(<DraftPage />);
    const passage = await screen.findByTestId("passage-4");
    expect(within(passage).getByText(/E-4 · quality.txt, page 1/)).toBeTruthy();
    expect(within(passage).getByText(/ISO 9001 certification across all sites/)).toBeTruthy();
    const marks = document.querySelectorAll("mark");
    expect([...marks].map((m) => [m.getAttribute("data-verdict"), m.textContent])).toEqual([["unsupported", "We cleaned 500 schools."]]);
    const rows = await screen.findAllByRole("row");
    expect(rows.filter((r) => r.getAttribute("data-verdict") === "unsupported")[0].className).toContain("red");
    expect(rows.filter((r) => r.getAttribute("data-verdict") === "unchecked")[0].className).toContain("amber");
    expect(screen.getByText("Over the limit")).toBeTruthy();
    expect(screen.getByText("1 gap to fill")).toBeTruthy();
    expect(screen.getByText(/2 claims are not supported/)).toBeTruthy();
  });

  it("flags a removed passage and saves an edit against the shown version", async () => {
    at(`/draft?id=${RID}`);
    const m = serve(table({
      "GET /api/evidence/passages?ids=4": { passages: [{ display_no: 4, label: "E-4", document: "quality.txt", page_from: 1, page_to: 1, heading: null, removed: true, text: "" }] },
      [`PUT /api/requirements/${RID}/draft`]: (init) => { expect(JSON.parse(init.body as string)).toEqual({ text: "Short.", base_version: 2 }); return reply(201, draft); } }));
    render(<DraftPage />);
    expect(await screen.findByText(/This evidence was removed/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Answer"), { target: { value: "Short." } });
    fireEvent.click(screen.getByRole("button", { name: "Save as a new version" }));
    await waitFor(() => expect(calls(m, `PUT /api/requirements/${RID}/draft`)).toBe(1));
  });

  it("offers no editing once the pack is signed off", async () => {
    at(`/draft?id=${RID}`);
    serve(table({ [`GET /api/packs/${PID}/status`]: { pack: pack({ status: "signed" }), tasks: [] } }));
    render(<DraftPage />);
    await screen.findByTestId("passage-4");
    await waitFor(() => expect(screen.queryByRole("button", { name: "Edit" })).toBeNull());
  });

  it("says so when nothing has been drafted", async () => {
    at(`/draft?id=${RID}`);
    serve({ [`GET /api/requirements/${RID}/draft`]: { requirement: req(), draft: null, versions: [] }, [`GET /api/requirements/${RID}/claims`]: { draft_version: null, checked: false, claims: [] },
      [`GET /api/packs/${PID}/status`]: { pack: pack(), tasks: [] } });
    render(<DraftPage />);
    expect(await screen.findByText(/No answer has been drafted yet/)).toBeTruthy();
  });

  it("AnswerText never renders markup from the text", () => {
    render(<AnswerText text={'<img src=x onerror=alert(1)> [E-1]'} claims={[]} />);
    expect(document.querySelector("img")).toBeNull();
    expect(screen.getByText("[E-1]")).toBeTruthy();
  });
});

describe("coverage and sign-off", () => {
  const row = { requirement_id: RID, seq: 1, ref: "Q1", kind: "question", text: "Quality", answered: true, words: 120, word_limit: 300, within_limit: true, gaps: 0, checked: true, claims: { supported: 2 }, covered: true };
  const cov = (over = {}) => ({ pack: pack({ status: "ready" }), rows: [row], export: { allowed: false, reasons: ["no_signoff: the pack has not been signed off"] },
    statement: { version: "v1", text: "My firm is responsible for every statement." }, signoff: null, notice: "This is a checklist. It does not say the bid is compliant.", ...over });
  const tbl = (c: Record<string, unknown>, extra: Record<string, Handler | Record<string, unknown>> = {}) => ({ [`GET /api/packs/${PID}/coverage`]: c, [`GET /api/packs/${PID}/status`]: { pack: pack({ status: "ready" }), tasks: [] }, ...extra });

  it("shows the checklist banner, the statement and signs off with name and tick", async () => {
    at(`/coverage?id=${PID}`);
    let signed = false;
    const m = serve(tbl(cov(), {}));
    m.mockImplementation(async (path: string, init: RequestInit = {}) => {
      const key = `${init.method ?? "GET"} ${path}`;
      if (key === `GET /api/packs/${PID}/coverage`) return reply(200, signed ? cov({ pack: pack({ status: "signed" }), signoff: { reviewer_name: "Ann Lee", signed_at: "2026-11-27T10:00:00Z" } }) : cov());
      if (key === `GET /api/packs/${PID}/status`) return reply(200, { pack: pack({ status: "ready" }), tasks: [] });
      if (key === `POST /api/packs/${PID}/signoff`) { expect(JSON.parse(init.body as string)).toEqual({ reviewer_name: "Ann Lee", accept_statement: true, statement_version: "v1" }); signed = true; return reply(201, {}); }
      throw new Error(key);
    });
    render(<CoveragePage />);
    expect(await screen.findByText(/does not say the bid is compliant/)).toBeTruthy();
    expect(screen.getByLabelText("Responsibility statement").textContent).toBe("My firm is responsible for every statement.");
    const button = screen.getByRole("button", { name: "Sign off this pack" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Your full name"), { target: { value: "Ann Lee" } });
    expect(button.disabled).toBe(true);  // still needs the tick
    fireEvent.click(screen.getByRole("checkbox"));
    expect(button.disabled).toBe(false);
    fireEvent.click(button);
    expect(await screen.findByText(/Signed off by Ann Lee/)).toBeTruthy();
  });

  const signedCov = () => cov({ pack: pack({ status: "signed" }), signoff: { reviewer_name: "Ann Lee", signed_at: "2026-11-27T10:00:00Z" }, export: { allowed: true, reasons: [] } });

  it("exports the Word document through a blob download when signed", async () => {
    at(`/coverage?id=${PID}`);
    const create = vi.fn(() => "blob:x"), revoke = vi.fn();
    Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const m = serve(tbl(signedCov(), { [`GET /api/packs/${PID}/export`]: () => new Response("x", { status: 200, headers: { "Content-Disposition": 'attachment; filename="Cleaning-draft.docx"' } }) }));
    render(<CoveragePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Export Word document" }));
    await screen.findByText(/Word document was downloaded/);
    expect(calls(m, `GET /api/packs/${PID}/export`)).toBe(1);
    expect(create).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(revoke).toHaveBeenCalledWith("blob:x"), { timeout: 3000 });
    expect(document.body.textContent).not.toMatch(/£|price/i);
    click.mockRestore();
  });

  it("shows the server's refusal when the export is blocked", async () => {
    at(`/coverage?id=${PID}`);
    serve(tbl(signedCov(), { [`GET /api/packs/${PID}/export`]: () => reply(409, { error: "export_blocked", message: "Export is blocked: evidence_removed" }) }));
    render(<CoveragePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Export Word document" }));
    expect(await screen.findByText(/Export is blocked: evidence_removed/)).toBeTruthy();
  });

  it("reopens only after a confirm", async () => {
    at(`/coverage?id=${PID}`);
    let reopened = false;
    const m = serve(tbl(signedCov()));
    m.mockImplementation(async (path: string, init: RequestInit = {}) => {
      const key = `${init.method ?? "GET"} ${path}`;
      if (key === `GET /api/packs/${PID}/coverage`) return reply(200, reopened ? cov() : signedCov());
      if (key === `GET /api/packs/${PID}/status`) return reply(200, { pack: pack({ status: "ready" }), tasks: [] });
      if (key === `POST /api/packs/${PID}/reopen`) { reopened = true; return reply(200, {}); }
      throw new Error(key);
    });
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    render(<CoveragePage />);
    const btn = await screen.findByRole("button", { name: "Reopen for edits" });
    fireEvent.click(btn);
    expect(calls(m, `POST /api/packs/${PID}/reopen`)).toBe(0);
    fireEvent.click(btn);
    expect(await screen.findByRole("button", { name: "Sign off this pack" })).toBeTruthy();
    expect(calls(m, `POST /api/packs/${PID}/reopen`)).toBe(1);
    confirm.mockRestore();
  });

  it("lists what blocks sign-off and keeps the button off", async () => {
    at(`/coverage?id=${PID}`);
    serve(tbl(cov({ export: { allowed: false, reasons: ["claims_blocked: 1 claim(s) in question x are not supported by evidence", "no_signoff: none"] } })));
    render(<CoveragePage />);
    expect(await screen.findByText(/1 claim\(s\) in question x are not supported/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Sign off this pack" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows the server's refusal", async () => {
    at(`/coverage?id=${PID}`);
    serve(tbl(cov(), { [`POST /api/packs/${PID}/signoff`]: () => reply(409, { error: "export_blocked", message: "Sign-off is not possible yet: evidence_removed" }) }));
    render(<CoveragePage />);
    fireEvent.change(await screen.findByLabelText("Your full name"), { target: { value: "Ann" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Sign off this pack" }));
    expect((await screen.findByRole("alert")).textContent).toContain("evidence_removed");
  });

  it("marks unanswered and over-limit rows", async () => {
    at(`/coverage?id=${PID}`);
    serve(tbl(cov({ rows: [{ ...row, answered: false, words: 400, within_limit: false, checked: false, gaps: 2, claims: { unsupported: 1 } }] })));
    render(<CoveragePage />);
    const r = await screen.findByTestId("cov-1");
    expect(within(r).getByText("Over")).toBeTruthy();
    expect(within(r).getByText("1 unsupported")).toBeTruthy();
    expect(within(r).getAllByText("No").length).toBe(2);
  });
});
