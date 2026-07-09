import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { ChatPanel } from "./ChatPanel";

afterEach(() => vi.restoreAllMocks());

const IDLE = { busy: false, reason: "idle", book_id: null, pause_requested: false } as const;
const BUSY = { busy: true, reason: "ingesting", book_id: "other-book", pause_requested: false } as const;

describe("ChatPanel", () => {
  it("loads history and sends a question", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "ask").mockResolvedValue({
      answer: "fork() 创建新进程", citations: [], triggered_tool: null,
      total_tokens: 10, latency_s: 0.5,
    });

    render(<ChatPanel bookId="ostep" conversationId="c1" status={IDLE} />);

    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    const input = screen.getByPlaceholderText("输入问题");
    await userEvent.type(input, "fork 是什么？");
    await userEvent.click(screen.getByText("发送"));

    await screen.findByText("fork() 创建新进程");
    expect(screen.getByText("fork 是什么？")).toBeInTheDocument();
  });

  it("disables input and send when busy", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });

    render(<ChatPanel bookId="ostep" conversationId="c1" status={BUSY} />);

    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    expect(screen.getByPlaceholderText("正在导入书籍，请稍后…")).toBeDisabled();
    expect(screen.getByText("发送")).toBeDisabled();
  });
});
