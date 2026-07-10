import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, afterEach } from "vitest";
import * as client from "../api/client";
import { BookGrid } from "./BookGrid";

vi.mock("../windowManager", () => ({ openOrFocusWindow: vi.fn() }));
import { openOrFocusWindow } from "../windowManager";

afterEach(() => vi.restoreAllMocks());

describe("BookGrid", () => {
  it("renders one card per book plus a trailing add tile", async () => {
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep", "civil-law"] });
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });

    render(<BookGrid />);

    expect(await screen.findByText("ostep")).toBeInTheDocument();
    expect(screen.getByText("civil-law")).toBeInTheDocument();
    expect(screen.getByLabelText("新建书")).toBeInTheDocument();
  });

  it("creating a new book opens its import window and inserts a card before the add tile", async () => {
    const user = userEvent.setup();
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });

    render(<BookGrid />);
    await user.click(screen.getByLabelText("新建书"));
    await user.type(screen.getByLabelText("新书 book_id"), "new-book");
    await user.click(screen.getByText("确定"));

    expect(openOrFocusWindow).toHaveBeenCalledWith("import", "new-book", "new-book");
    expect(await screen.findByText("new-book")).toBeInTheDocument();
  });
});
