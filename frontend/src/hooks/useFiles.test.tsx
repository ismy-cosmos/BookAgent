import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "@/api/client";
import { useFiles } from "./useFiles";

afterEach(() => vi.restoreAllMocks());

describe("useFiles", () => {
  it("loads files for the given book", async () => {
    vi.spyOn(client, "listFiles").mockResolvedValue({ files: ["ch01.pdf", "ch02.pdf"] });

    const { result } = renderHook(() => useFiles("ostep"));

    await waitFor(() => expect(result.current.files).toEqual(["ch01.pdf", "ch02.pdf"]));
    expect(client.listFiles).toHaveBeenCalledWith("ostep");
  });

  it("reloads when bookId changes", async () => {
    vi.spyOn(client, "listFiles")
      .mockResolvedValueOnce({ files: ["a.pdf"] })
      .mockResolvedValueOnce({ files: ["b.pdf"] });

    const { result, rerender } = renderHook(({ bookId }) => useFiles(bookId), {
      initialProps: { bookId: "ostep" },
    });
    await waitFor(() => expect(result.current.files).toEqual(["a.pdf"]));

    rerender({ bookId: "civil-law" });
    await waitFor(() => expect(result.current.files).toEqual(["b.pdf"]));
  });

  it("removes a file and refreshes", async () => {
    vi.spyOn(client, "listFiles")
      .mockResolvedValueOnce({ files: ["a.pdf"] })
      .mockResolvedValueOnce({ files: [] });
    vi.spyOn(client, "deleteFile").mockResolvedValue({ deleted_file: "a.pdf", book_id: "ostep" });

    const { result } = renderHook(() => useFiles("ostep"));
    await waitFor(() => expect(result.current.files).toEqual(["a.pdf"]));

    await act(async () => {
      await result.current.remove("a.pdf");
    });

    expect(result.current.files).toEqual([]);
  });

  it("treats 404 as an empty file list (brand-new book)", async () => {
    vi.spyOn(client, "listFiles").mockRejectedValue(
      new client.ApiError(404, "book_id 'new-book' 不存在"),
    );

    const { result } = renderHook(() => useFiles("new-book"));

    await waitFor(() => expect(client.listFiles).toHaveBeenCalled());
    expect(result.current.files).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});
