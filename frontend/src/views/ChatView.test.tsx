import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { ChatView } from "./ChatView";

afterEach(() => vi.restoreAllMocks());

describe("ChatView", () => {
  it("refreshes the conversation list after a question is answered, so the title updates", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listConversations")
      .mockResolvedValueOnce({ conversations: [{ id: "c1", title: "新对话", updated_at: "" }] })
      .mockResolvedValueOnce({ conversations: [{ id: "c1", title: "fork 是什么？", updated_at: "" }] });
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "新对话", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "ask").mockResolvedValue({
      answer: "fork 创建子进程", citations: [], triggered_tool: null,
      total_tokens: 10, latency_s: 0.5, used_calculate: false, attempted_retrieve: false,
    });

    render(<ChatView bookId="ostep" />);

    // 用 getByRole 按可访问名字查——"新建对话"按钮的可访问名字跟这个
    // 默认标题也叫"新对话"的对话项不会撞在一起（前者 aria-label 是
    // "新建对话"），screen.findByText 直接查裸文本反而会因为两处都有
    // "新对话"这几个字而多元素匹配报错。
    await userEvent.click(await screen.findByRole("button", { name: "新对话" }));
    const input = await screen.findByPlaceholderText("输入问题");
    await userEvent.type(input, "fork 是什么？");
    await userEvent.click(screen.getByText("发送"));

    await waitFor(() => expect(client.listConversations).toHaveBeenCalledTimes(2));
    // 发完之后左栏标题和右侧问题气泡会显示同一句文字——不能用
    // screen.findByText 全局查，会因为匹配到两个元素直接报错，
    // 必须把查询范围限定在左栏（nav[aria-label="对话列表"]）内。
    const sidebar = screen.getByRole("navigation", { name: "对话列表" });
    expect(within(sidebar).getByText("fork 是什么？")).toBeInTheDocument();
  });

  it("creating a new conversation calls the create API", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listConversations").mockResolvedValue({ conversations: [] });
    const createSpy = vi.spyOn(client, "createConversation").mockResolvedValue({
      id: "c2", book_id: "ostep", title: "新对话", created_at: "", updated_at: "", turns: [],
    });

    render(<ChatView bookId="ostep" />);

    await userEvent.click(await screen.findByRole("button", { name: "新建对话" }));
    expect(createSpy).toHaveBeenCalledWith("ostep");
  });
});
