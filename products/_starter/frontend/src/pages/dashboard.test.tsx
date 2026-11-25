import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { beforeEach, describe, expect, it, vi } from "vitest";
import { reply, stubFetch, ME } from "../test-utils";
import { Dashboard } from "./app";

let fetchMock: ReturnType<typeof vi.fn>;
const note = (i: number) => ({ id: `n${i}`, title: `Note ${i}`, body: "", summary: null, created_at: "", updated_at: "" });

beforeEach(() => { fetchMock = stubFetch(); });

describe("Dashboard notes list (T-86)", () => {
  it("offers a retry instead of loading forever when the list fails to load", async () => {
    let fail = true;
    fetchMock.mockImplementation(async () => fail ? reply(502, { error: "x", message: "Bad gateway" }) : reply(200, { items: [note(1)], total: 1 }));
    render(<Dashboard me={ME} />);
    expect(await screen.findByText("We couldn't load your notes.")).toBeTruthy();
    expect(screen.queryByText("Loading…")).toBeNull();
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Note 1")).toBeTruthy();
  });

  it("lets you reach notes beyond the first page", async () => {
    fetchMock.mockImplementation(async (path: string) => path.includes("offset=2")
      ? reply(200, { items: [note(3)], total: 3 })
      : reply(200, { items: [note(1), note(2)], total: 3 }));
    render(<Dashboard me={ME} />);
    await screen.findByText("Note 2");
    fireEvent.click(screen.getByRole("button", { name: /Show more notes \(2 of 3\)/ }));
    await waitFor(() => expect(screen.getByText("Note 3")).toBeTruthy());
    expect(screen.queryByRole("button", { name: /Show more/ })).toBeNull();
  });

  it("lets long unbroken text wrap instead of widening the page", async () => {
    fetchMock.mockImplementation(async () => reply(200, { items: [{ ...note(1), title: "x".repeat(150), body: "y".repeat(500) }], total: 1 }));
    render(<Dashboard me={ME} />);
    expect((await screen.findByText("x".repeat(150))).className).toContain("break-words");
    expect(screen.getByText("y".repeat(500)).className).toContain("break-words");
  });

  it("hides Show more after deleting from a fully loaded list", async () => {
    fetchMock.mockImplementation(async (_path: string, init?: RequestInit) => init?.method === "DELETE"
      ? reply(204)
      : reply(200, { items: [note(1), note(2), note(3)], total: 3 }));
    render(<Dashboard me={ME} />);
    await screen.findByText("Note 3");
    expect(screen.queryByRole("button", { name: /Show more/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Delete Note 1" }));
    await waitFor(() => expect(screen.queryByText("Note 1")).toBeNull());
    expect(screen.queryByRole("button", { name: /Show more/ })).toBeNull();
  });

  it("trusts the total from the latest page when it changes between pages", async () => {
    fetchMock.mockImplementation(async (path: string) => path.includes("offset=2")
      ? reply(200, { items: [note(3)], total: 3 }) // a note was deleted elsewhere: 4 became 3
      : reply(200, { items: [note(1), note(2)], total: 4 }));
    render(<Dashboard me={ME} />);
    await screen.findByText("Note 2");
    fireEvent.click(screen.getByRole("button", { name: /Show more notes \(2 of 4\)/ }));
    await screen.findByText("Note 3");
    expect(screen.queryByRole("button", { name: /Show more/ })).toBeNull();
  });

  it("shows a note once when the next page repeats an id", async () => {
    fetchMock.mockImplementation(async (path: string) => path.includes("offset=2")
      ? reply(200, { items: [note(2), note(3)], total: 3 })
      : reply(200, { items: [note(1), note(2)], total: 3 }));
    render(<Dashboard me={ME} />);
    await screen.findByText("Note 2");
    fireEvent.click(screen.getByRole("button", { name: /Show more/ }));
    await screen.findByText("Note 3");
    expect(screen.getAllByText("Note 2")).toHaveLength(1);
  });

  it("lets a long summary wrap", async () => {
    fetchMock.mockImplementation(async () => reply(200, { items: [{ ...note(1), summary: "z".repeat(400) }], total: 1 }));
    render(<Dashboard me={ME} />);
    expect((await screen.findByTestId("summary")).className).toContain("break-words");
  });

  it("keeps Show more disabled while it loads, even after Summarise finishes", async () => {
    let release: (r: Response) => void = () => {};
    fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path.includes("offset=2")) return new Promise<Response>((resolve) => { release = resolve; });
      if (init?.method === "POST") return reply(200, { ...note(1), summary: "short" });
      return reply(200, { items: [note(1), note(2)], total: 3 });
    });
    render(<Dashboard me={ME} />);
    await screen.findByText("Note 2");
    fireEvent.click(screen.getByRole("button", { name: /Show more/ }));
    fireEvent.click(screen.getAllByRole("button", { name: "Summarise" })[0]);
    await screen.findByText("short");
    const pending = screen.getByRole("button", { name: /Working/ }) as HTMLButtonElement;
    expect(pending.disabled).toBe(true);
    fireEvent.click(pending);
    expect(fetchMock.mock.calls.filter(([p]) => String(p).includes("offset=2"))).toHaveLength(1);
    release(reply(200, { items: [note(3)], total: 3 }));
    await screen.findByText("Note 3");
  });

  it("drops a load-more response that started before the list was reloaded", async () => {
    let release: (r: Response) => void = () => {};
    fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path.includes("offset=2")) return new Promise<Response>((resolve) => { release = resolve; });
      if (init?.method === "POST") return reply(201, note(9));
      return reply(200, { items: [note(1), note(2)], total: 3 });
    });
    render(<Dashboard me={ME} />);
    await screen.findByText("Note 2");
    fireEvent.click(screen.getByRole("button", { name: /Show more/ }));
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Fresh" } });
    fireEvent.click(screen.getByRole("button", { name: "Save note" }));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([p, i]) => p === "/api/notes" && i?.method === "GET").length).toBeGreaterThanOrEqual(2));
    await waitFor(() => expect((screen.getByLabelText("Title") as HTMLInputElement).value).toBe(""));
    release(reply(200, { items: [note(3)], total: 3 }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Show more notes \(2 of 3\)/ })).toBeTruthy());
    expect(screen.queryByText("Note 3")).toBeNull();
  });
});
