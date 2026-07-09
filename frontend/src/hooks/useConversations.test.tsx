import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { useConversations } from "./useConversations";

afterEach(() => vi.restoreAllMocks());

describe("useConversations", () => {
  it("loads conversations on mount", async () => {
    vi.spyOn(client, "listConversations").mockResolvedValue({
      conversations: [{ id: "c1", title: "fork 是什么？", updated_at: "" }],
    });

    const { result } = renderHook(() => useConversations("ostep"));

    await waitFor(() =>
      expect(result.current.conversations).toEqual([
        { id: "c1", title: "fork 是什么？", updated_at: "" },
      ]),
    );
  });

  it("creates a new conversation and refreshes", async () => {
    vi.spyOn(client, "createConversation").mockResolvedValue({
      id: "c2", book_id: "ostep", title: "新对话", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "listConversations")
      .mockResolvedValueOnce({ conversations: [] })
      .mockResolvedValueOnce({ conversations: [{ id: "c2", title: "新对话", updated_at: "" }] });

    const { result } = renderHook(() => useConversations("ostep"));
    await waitFor(() => expect(client.listConversations).toHaveBeenCalled());

    await act(async () => {
      await result.current.create();
    });

    expect(result.current.conversations).toEqual([{ id: "c2", title: "新对话", updated_at: "" }]);
  });

  it("deletes a conversation and refreshes", async () => {
    vi.spyOn(client, "deleteConversation").mockResolvedValue({ deleted: "c1" });
    vi.spyOn(client, "listConversations")
      .mockResolvedValueOnce({ conversations: [{ id: "c1", title: "x", updated_at: "" }] })
      .mockResolvedValueOnce({ conversations: [] });

    const { result } = renderHook(() => useConversations("ostep"));
    await waitFor(() => expect(client.listConversations).toHaveBeenCalled());

    await act(async () => {
      await result.current.remove("c1");
    });

    expect(result.current.conversations).toEqual([]);
  });
});
