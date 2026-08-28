import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "@/api/client";
import { useChat } from "./useChat";

afterEach(() => vi.restoreAllMocks());

describe("useChat", () => {
  it("loads history on mount", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "",
      turns: [{ question: "q", answer: "a", citations: [], used_calculate: false, attempted_retrieve: false }],
    });

    const { result } = renderHook(() => useChat("ostep", "c1"));

    await waitFor(() => expect(result.current.history).toHaveLength(1));
    expect(result.current.history[0].question).toBe("q");
  });

  it("sends a question and appends to local history with used_calculate/attempted_retrieve", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "ask").mockResolvedValue({
      answer: "fork() 创建新进程", citations: [], triggered_tool: null,
      total_tokens: 10, latency_s: 0.5, used_calculate: false, attempted_retrieve: true,
    });

    const { result } = renderHook(() => useChat("ostep", "c1"));
    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    await act(async () => {
      await result.current.send("fork 是什么？");
    });

    expect(result.current.history).toEqual([
      {
        question: "fork 是什么？", answer: "fork() 创建新进程", citations: [],
        used_calculate: false, attempted_retrieve: true,
      },
    ]);
  });

  it("sets pendingQuestion while a send is in flight, clears it after", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    let resolveAsk: (v: Awaited<ReturnType<typeof client.ask>>) => void;
    vi.spyOn(client, "ask").mockReturnValue(
      new Promise((resolve) => { resolveAsk = resolve; }),
    );

    const { result } = renderHook(() => useChat("ostep", "c1"));
    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    let sendPromise: Promise<boolean>;
    act(() => {
      sendPromise = result.current.send("问题");
    });
    expect(result.current.pendingQuestion).toBe("问题");

    await act(async () => {
      resolveAsk({
        answer: "答案", citations: [], triggered_tool: null,
        total_tokens: 1, latency_s: 0.1, used_calculate: false, attempted_retrieve: false,
      });
      await sendPromise;
    });

    expect(result.current.pendingQuestion).toBeNull();
  });

  it("send returns false and sets error on failure, does not touch history", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "ask").mockRejectedValue(new Error("正在导入书籍，请稍后再问"));

    const { result } = renderHook(() => useChat("ostep", "c1"));
    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.send("问题");
    });

    expect(ok).toBe(false);
    expect(result.current.error).toBe("正在导入书籍，请稍后再问");
    expect(result.current.history).toEqual([]);
  });

  it("clearError resets error to null", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "ask").mockRejectedValue(new Error("失败"));

    const { result } = renderHook(() => useChat("ostep", "c1"));
    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());
    await act(async () => {
      await result.current.send("问题");
    });
    expect(result.current.error).toBe("失败");

    act(() => result.current.clearError());
    expect(result.current.error).toBeNull();
  });
});
