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

  it("creating a new conversation immediately switches to it, not requiring a manual click", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listConversations").mockResolvedValue({ conversations: [] });
    vi.spyOn(client, "createConversation").mockResolvedValue({
      id: "c2", book_id: "ostep", title: "新对话", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c2", book_id: "ostep", title: "新对话", created_at: "", updated_at: "", turns: [],
    });

    render(<ChatView bookId="ostep" />);

    await userEvent.click(await screen.findByRole("button", { name: "新建对话" }));

    // ChatPanel 出现（说明右栏已经切到刚建出来的对话），不需要用户
    // 再手动去左栏点一次。
    await screen.findByPlaceholderText("输入问题");
    expect(client.getConversation).toHaveBeenCalledWith("ostep", "c2");
  });

  it("deleting the currently open conversation clears the chat panel", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listConversations")
      .mockResolvedValueOnce({ conversations: [{ id: "c1", title: "旧对话", updated_at: "" }] })
      .mockResolvedValueOnce({ conversations: [] });
    vi.spyOn(client, "getConversation").mockResolvedValue({
      id: "c1", book_id: "ostep", title: "旧对话", created_at: "", updated_at: "", turns: [],
    });
    vi.spyOn(client, "deleteConversation").mockResolvedValue({ deleted: "c1" });

    render(<ChatView bookId="ostep" />);

    await userEvent.click(await screen.findByRole("button", { name: "旧对话" }));
    await screen.findByPlaceholderText("输入问题");

    await userEvent.click(screen.getByText("删除"));

    // 删的是当前正在看的这个对话——右栏应该立刻清空，不能继续显示
    // 已经被删掉的对话内容，让用户没法判断到底删没删成功。
    await waitFor(() => expect(screen.queryByPlaceholderText("输入问题")).not.toBeInTheDocument());
  });
});
