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
      total_tokens: 10, latency_s: 0.5, used_calculate: false, attempted_retrieve: true,
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

  it("shows the question immediately with a thinking indicator before the answer arrives", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    let resolveAsk: (v: Awaited<ReturnType<typeof client.ask>>) => void;
    vi.spyOn(client, "ask").mockReturnValue(
      new Promise((resolve) => { resolveAsk = resolve; }),
    );

    render(<ChatPanel bookId="ostep" conversationId="c1" status={IDLE} />);
    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    const input = screen.getByPlaceholderText("输入问题");
    await userEvent.type(input, "fork 是什么？");
    await userEvent.click(screen.getByText("发送"));

    expect(screen.getByText("fork 是什么？")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "思考中" })).toBeInTheDocument();

    resolveAsk!({
      answer: "fork() 创建新进程", citations: [], triggered_tool: null,
      total_tokens: 10, latency_s: 0.5, used_calculate: false, attempted_retrieve: false,
    });
    await screen.findByText("本轮未重新检索原文");
  });

  it("renders citation pills, strips known tags from display text, and opens ChunkDetailModal on click", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "",
      turns: [{
        question: "fork 是什么？",
        answer: "fork 创建子进程\n[引用来源：f.pdf p.1]",
        citations: [{ chunk_id: "c1", source_file: "f.pdf", element_type: "text", citation: "f.pdf p.1", score: 0.9 }],
        used_calculate: false,
        attempted_retrieve: true,
      }],
    });
    vi.spyOn(client, "getChunk").mockResolvedValue({
      chunk_id: "c1", content: "chunk 原文", source_file: "f.pdf", element_type: "text",
      page_start: 1, page_end: 1, start_sec: null, end_sec: null, low_confidence: false,
    });

    render(<ChatPanel bookId="ostep" conversationId="c1" status={IDLE} />);

    const answerBubble = await screen.findByText("fork 创建子进程");
    expect(answerBubble.textContent).not.toContain("引用来源");

    await userEvent.click(screen.getByText("f.pdf p.1"));
    await screen.findByText("chunk 原文");
  });

  it("shows '已使用计算工具' label when used_calculate is true", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "",
      turns: [{
        question: "3.2GB 是多少字节？",
        answer: "约 3435973836.8 字节",
        citations: [],
        used_calculate: true,
        attempted_retrieve: false,
      }],
    });

    render(<ChatPanel bookId="ostep" conversationId="c1" status={IDLE} />);

    await screen.findByText("已使用计算工具");
  });

  it("shows an error toast and keeps the typed question when send fails", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "ask").mockRejectedValue(new Error("正在导入书籍，请稍后再问"));

    render(<ChatPanel bookId="ostep" conversationId="c1" status={IDLE} />);
    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    const input = screen.getByPlaceholderText("输入问题");
    await userEvent.type(input, "再讲讲 TLB");
    await userEvent.click(screen.getByText("发送"));

    expect(await screen.findByRole("alert")).toHaveTextContent("正在导入书籍，请稍后再问");
    expect(screen.getByPlaceholderText("输入问题")).toHaveValue("再讲讲 TLB");
  });

  it("calls onSent after a successful send", async () => {
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "t", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "ask").mockResolvedValue({
      answer: "答案", citations: [], triggered_tool: null,
      total_tokens: 1, latency_s: 0.1, used_calculate: false, attempted_retrieve: false,
    });
    const onSent = vi.fn();

    render(<ChatPanel bookId="ostep" conversationId="c1" status={IDLE} onSent={onSent} />);
    await waitFor(() => expect(client.getConversation).toHaveBeenCalled());

    const input = screen.getByPlaceholderText("输入问题");
    await userEvent.type(input, "问题");
    await userEvent.click(screen.getByText("发送"));

    await waitFor(() => expect(onSent).toHaveBeenCalledOnce());
  });
});
