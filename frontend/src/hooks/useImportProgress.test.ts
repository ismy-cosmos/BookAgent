import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "@/api/client";
import { useImportProgress } from "./useImportProgress";

afterEach(() => vi.restoreAllMocks());

describe("useImportProgress", () => {
  it("fetches progress immediately on mount", async () => {
    vi.spyOn(client, "getProgress").mockResolvedValue({
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "parsing", current_file: 1, total_files: 2,
                  current_image: null, total_images: null },
      last_result: null,
    });

    const { result } = renderHook(() => useImportProgress());

    await waitFor(() => expect(result.current.progress?.busy).toBe(true));
    expect(result.current.progress?.progress?.stage).toBe("parsing");
  });

  it("stays null while every poll fails (unreachable is useStatus's job)", async () => {
    vi.spyOn(client, "getProgress").mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useImportProgress());

    await waitFor(() => expect(client.getProgress).toHaveBeenCalled());
    expect(result.current.progress).toBeNull();
  });
});
