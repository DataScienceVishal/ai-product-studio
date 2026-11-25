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
});
