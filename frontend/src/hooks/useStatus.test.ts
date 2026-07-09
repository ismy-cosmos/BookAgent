import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { useStatus } from "./useStatus";

afterEach(() => vi.restoreAllMocks());

describe("useStatus", () => {
  it("fetches status immediately on mount", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
    });

    const { result } = renderHook(() => useStatus());

    await waitFor(() => expect(result.current.status.busy).toBe(true));
    expect(result.current.status.book_id).toBe("ostep");
    expect(result.current.unreachable).toBe(false);
  });

  it("marks unreachable when the request fails", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useStatus());

    await waitFor(() => expect(result.current.unreachable).toBe(true));
  });
});
