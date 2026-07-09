import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { useChat } from "./useChat";

afterEach(() => vi.restoreAllMocks());

const IDLE = { busy: false, reason: "idle", book_id: null, pause_requested: false } as const;

describe("useChat", () => {
  it("loads history on mount", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "",
      turns: [{ question: "q", answer: "a", citations: [] }],
    });

    const { result } = renderHook(() => useChat("ostep", "c1"));

    await waitFor(() => expect(result.current.history).toHaveLength(1));
    expect(result.current.history[0].question).toBe("q");
  });

  it("sends a question and appends to local history", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "ask").mockResolvedValue({
      answer: "fork() 创建新进程", citations: [], triggered_tool: null,
      total_tokens: 10, latency_s: 0.5,
    });

    const { result } = renderHook(() => useChat("ostep", "c1"));
    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    await act(async () => {
      await result.current.send("fork 是什么？");
    });

    expect(result.current.history).toEqual([
      { question: "fork 是什么？", answer: "fork() 创建新进程", citations: [] },
    ]);
  });
});
