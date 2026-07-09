import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { useStagedFiles } from "./useStagedFiles";

afterEach(() => vi.restoreAllMocks());

describe("useStagedFiles", () => {
  it("loads staged files on mount", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/data/ch01.pdf"] });

    const { result } = renderHook(() => useStagedFiles("ostep"));

    await waitFor(() => expect(result.current.files).toEqual(["/data/ch01.pdf"]));
    expect(client.listStagedFiles).toHaveBeenCalledWith("ostep");
  });

  it("adds multiple paths sequentially and keeps the last response", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    const addSpy = vi.spyOn(client, "addStagedFile")
      .mockResolvedValueOnce({ files: ["/a.pdf"] })
      .mockResolvedValueOnce({ files: ["/a.pdf", "/b.epub"] });

    const { result } = renderHook(() => useStagedFiles("ostep"));
    await waitFor(() => expect(client.listStagedFiles).toHaveBeenCalled());

    await act(async () => {
      await result.current.add(["/a.pdf", "/b.epub"]);
    });

    expect(addSpy).toHaveBeenNthCalledWith(1, "ostep", "/a.pdf");
    expect(addSpy).toHaveBeenNthCalledWith(2, "ostep", "/b.epub");
    expect(result.current.files).toEqual(["/a.pdf", "/b.epub"]);
  });

  it("removes a staged file", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    vi.spyOn(client, "removeStagedFile").mockResolvedValue({ files: [] });

    const { result } = renderHook(() => useStagedFiles("ostep"));
    await waitFor(() => expect(result.current.files).toEqual(["/a.pdf"]));

    await act(async () => {
      await result.current.remove("/a.pdf");
    });

    expect(result.current.files).toEqual([]);
  });

  it("records the error message when add fails", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    vi.spyOn(client, "addStagedFile").mockRejectedValue(
      new client.ApiError(400, "不支持的文件类型：.txt"),
    );

    const { result } = renderHook(() => useStagedFiles("ostep"));
    await waitFor(() => expect(client.listStagedFiles).toHaveBeenCalled());

    await act(async () => {
      await result.current.add(["/notes.txt"]);
    });

    expect(result.current.error).toBe("不支持的文件类型：.txt");
  });
});
