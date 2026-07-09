import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { BookList } from "./BookList";
import type { Status } from "../api/types";

afterEach(() => vi.restoreAllMocks());

const IDLE: Status = { busy: false, reason: "idle", book_id: null, pause_requested: false };

describe("BookList", () => {
  it("renders books and selects one on click", async () => {
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep"] });
    const onSelectBook = vi.fn();

    render(<BookList status={IDLE} selectedBook={null} onSelectBook={onSelectBook} />);

    const bookButton = await screen.findByText("ostep");
    await userEvent.click(bookButton);
    expect(onSelectBook).toHaveBeenCalledWith("ostep");
  });

  it("disables delete only for the book currently being imported", async () => {
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep", "civil-law"] });
    const busyStatus: Status = { busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false };

    render(<BookList status={busyStatus} selectedBook={null} onSelectBook={vi.fn()} />);

    await screen.findByText("ostep");
    const deleteButtons = screen.getAllByText("删除");
    // ostep 在前，civil-law 在后（跟 listBooks mock 返回顺序一致）
    expect(deleteButtons[0]).toBeDisabled();
    expect(deleteButtons[1]).not.toBeDisabled();
  });

  it("creates a new book id and selects it", async () => {
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    const onSelectBook = vi.fn();

    render(<BookList status={IDLE} selectedBook={null} onSelectBook={onSelectBook} />);

    await userEvent.click(screen.getByText("新建书"));
    await userEvent.type(screen.getByLabelText("新书 book_id"), "my-new-book");
    await userEvent.click(screen.getByText("确定"));

    expect(onSelectBook).toHaveBeenCalledWith("my-new-book");
  });

  it("shows confirm dialog and deletes on confirm", async () => {
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep"] });
    const deleteSpy = vi.spyOn(client, "deleteBook").mockResolvedValue({ deleted: "ostep" });

    render(<BookList status={IDLE} selectedBook={null} onSelectBook={vi.fn()} />);

    await screen.findByText("ostep");
    await userEvent.click(screen.getByText("删除"));
    expect(screen.getByText(/确定要删除/)).toBeInTheDocument();

    await userEvent.click(screen.getByText("确认删除"));
    expect(deleteSpy).toHaveBeenCalledWith("ostep");
  });
});
