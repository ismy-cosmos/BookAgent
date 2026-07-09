import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { FileList } from "./FileList";

afterEach(() => vi.restoreAllMocks());

describe("FileList", () => {
  it("renders file names and initiates removal on delete click", async () => {
    vi.spyOn(client, "listFiles").mockResolvedValue({ files: ["ch01.pdf", "ch02.pdf"] });
    const deleteSpy = vi.spyOn(client, "deleteFile").mockResolvedValue({ deleted_file: "ch01.pdf", book_id: "ostep" });

    render(<FileList bookId="ostep" />);

    await screen.findByText("ch01.pdf");

    const deleteButtons = screen.getAllByText("删除");
    await userEvent.click(deleteButtons[0]);

    expect(screen.getByText(/确定要删除 'ch01.pdf'/)).toBeInTheDocument();
    await userEvent.click(screen.getByText("确认删除"));
    expect(deleteSpy).toHaveBeenCalledWith("ostep", "ch01.pdf");
  });

  it("shows empty state when no files", async () => {
    vi.spyOn(client, "listFiles").mockResolvedValue({ files: [] });

    render(<FileList bookId="ostep" />);

    await waitFor(() => expect(client.listFiles).toHaveBeenCalled());
    expect(screen.getByText("暂无已导入文件")).toBeInTheDocument();
  });
});
