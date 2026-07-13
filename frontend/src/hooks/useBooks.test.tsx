import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { useBooks } from "./useBooks";

vi.mock("../windowManager", () => ({
  closeBookWindows: vi.fn().mockResolvedValue(undefined),
  hasOpenWindows: vi.fn().mockResolvedValue(false),
}));
import { closeBookWindows, hasOpenWindows } from "../windowManager";

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
    expect(closeBookWindows).toHaveBeenCalledWith("ostep");
  });

  it("blocks renaming while the book's import or chat window is open", async () => {
    // 改名会改变 book_id，而窗口 label／窗口内部的 React 状态都是按旧
    // book_id 认定的——不去尝试迁移窗口，改名前先查窗口开没开，开着就
    // 直接拒绝，跟"改名冲突"走同一条失败回退路径。
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep"] });
    vi.mocked(hasOpenWindows).mockResolvedValueOnce(true);
    const renameBookSpy = vi.spyOn(client, "renameBook");

    const { result } = renderHook(() => useBooks());
    await waitFor(() => expect(result.current.books).toEqual(["ostep"]));

    let caught: unknown;
    await act(async () => {
      try {
        await result.current.rename("ostep", "new-name");
      } catch (e) {
        caught = e;
      }
    });

    expect(caught).toBeInstanceOf(Error);
    expect(renameBookSpy).not.toHaveBeenCalled();
    expect(result.current.error).toMatch(/ostep/);
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
