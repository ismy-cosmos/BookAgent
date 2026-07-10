import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { useBooks } from "./useBooks";

afterEach(() => vi.restoreAllMocks());

describe("useBooks", () => {
  it("loads books on mount", async () => {
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep", "civil-law"] });

    const { result } = renderHook(() => useBooks());

    await waitFor(() => expect(result.current.books).toEqual(["ostep", "civil-law"]));
  });

  it("removes a book and refreshes the list", async () => {
    vi.spyOn(client, "listBooks")
      .mockResolvedValueOnce({ books: ["ostep"] })
      .mockResolvedValueOnce({ books: [] });
    vi.spyOn(client, "deleteBook").mockResolvedValue({ deleted: "ostep" });

    const { result } = renderHook(() => useBooks());
    await waitFor(() => expect(result.current.books).toEqual(["ostep"]));

    await act(async () => {
      await result.current.remove("ostep");
    });

    expect(result.current.books).toEqual([]);
  });

  it("renames a book and refreshes the list", async () => {
    vi.spyOn(client, "listBooks")
      .mockResolvedValueOnce({ books: ["old"] })
      .mockResolvedValueOnce({ books: ["new"] });
    vi.spyOn(client, "renameBook").mockResolvedValue({ book_id: "new" });

    const { result } = renderHook(() => useBooks());
    await waitFor(() => expect(result.current.books).toEqual(["old"]));

    await act(async () => {
      await result.current.rename("old", "new");
    });

    expect(client.renameBook).toHaveBeenCalledWith("old", "new");
    expect(result.current.books).toEqual(["new"]);
  });
});
