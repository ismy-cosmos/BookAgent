import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, afterEach } from "vitest";
import * as client from "../api/client";
import { ApiError } from "../api/client";
import { BookGrid } from "./BookGrid";

async function createAndDeletePendingBook(user: ReturnType<typeof userEvent.setup>, id: string) {
  await user.click(screen.getByLabelText("新建书"));
  await user.type(screen.getByLabelText("新书 book_id"), id);
  await user.click(screen.getByText("确定"));
  expect(await screen.findByText(id)).toBeInTheDocument();
  await user.hover(screen.getByText(id).closest('[data-testid="book-card"]')!);
  fireEvent.click(screen.getByText("删除丛书"));
  await user.click(screen.getByText("确认删除"));
}

vi.mock("../windowManager", () => ({
  openOrFocusWindow: vi.fn(),
  closeBookWindows: vi.fn().mockResolvedValue(undefined),
}));
import { closeBookWindows, openOrFocusWindow } from "../windowManager";

afterEach(() => vi.restoreAllMocks());

describe("BookGrid", () => {
  it("renders one card per book plus a trailing add tile", async () => {
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep", "civil-law"] });
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });

    render(<BookGrid />);

    expect(await screen.findByText("ostep")).toBeInTheDocument();
    expect(screen.getByText("civil-law")).toBeInTheDocument();
    expect(screen.getByLabelText("新建书")).toBeInTheDocument();
  });

  it("creating a new book opens its import window and inserts a card before the add tile", async () => {
    const user = userEvent.setup();
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });

    render(<BookGrid />);
    await user.click(screen.getByLabelText("新建书"));
    await user.type(screen.getByLabelText("新书 book_id"), "new-book");
    await user.click(screen.getByText("确定"));

    expect(openOrFocusWindow).toHaveBeenCalledWith("import", "new-book", "new-book");
    expect(await screen.findByText("new-book")).toBeInTheDocument();
  });

  it("removing a pending book the backend never created (404) drops it locally", async () => {
    // 待导入的书在本地看起来"还没建过"，但不能光凭本地状态就跳过后端——
    // 必须真的打一次删除接口，让后端的忙碌检查说了算。这里后端确认
    // 从没为它建出真实 collection（404），本地记录可以放心摘掉。
    const user = userEvent.setup();
    const deleteBookSpy = vi.spyOn(client, "deleteBook")
      .mockRejectedValue(new ApiError(404, "book_id 'new-book' 不存在"));
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });

    render(<BookGrid />);
    await createAndDeletePendingBook(user, "new-book");

    expect(deleteBookSpy).toHaveBeenCalledWith("new-book");
    expect(screen.queryByText("new-book")).not.toBeInTheDocument();
    expect(closeBookWindows).toHaveBeenCalledWith("new-book");
  });

  it("does NOT remove a pending book that the backend reports as actively importing (409), and surfaces the error", async () => {
    // 回归测试：这是真正的安全漏洞——待导入的书如果已经在导入窗口点过
    // "开始导入"，后端会有一个真实任务在跑；这时候点删除必须让用户看到
    // 409，卡片绝不能消失。之前的实现完全没打后端就本地摘掉了卡片，
    // 导入还在后台继续跑，跑完第一个 chunk 入库时这本书会被重新建出来
    // （get_or_create_collection），造成"删了又自己冒出来"的假象。
    //
    // getStatus 这里仍然给 busy:false（不模拟"这本书正在导入"）——因为
    // BookCard 的删除按钮现在会在 importing 时正确置灰，真按钮已经点不
    // 进去了；这条测试改成模拟更真实的触发窗口：前端轮询有间隔（2秒），
    // 后端那一刻其实已经真的忙了，只是前端还没来得及感知、按钮还没禁用，
    // deleteBook 打过去时后端凭自己当下的真实状态照样会拒。
    const user = userEvent.setup();
    const deleteBookSpy = vi.spyOn(client, "deleteBook")
      .mockRejectedValue(new ApiError(409, "'new-book' 正在导入中，暂不可删除"));
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });

    render(<BookGrid />);
    await createAndDeletePendingBook(user, "new-book");

    expect(deleteBookSpy).toHaveBeenCalledWith("new-book");
    expect(screen.getByText("new-book")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("正在导入中，暂不可删除");
  });

  it("surfaces the error when deleting an already-existing book is rejected, instead of swallowing it", async () => {
    // 回归测试：已存在的书走 useBooks().remove()，之前 handleRemove 在它
    // 后面又多余调用了一次 refresh()——remove() 失败时刚把 409 错误存进
    // error，refresh() 自己那次 GET /books 只要成功就会把 error 立刻清空，
    // 错误提示实际上从来没机会显示出来，用户以为点了删除毫无反应。
    // getStatus 给 busy:false 的原因同上一条——按钮置灰后，这条测试真正
    // 要测的是"轮询还没跟上、后端已经拒绝"这个窗口。
    const user = userEvent.setup();
    vi.spyOn(client, "deleteBook")
      .mockRejectedValue(new ApiError(409, "'ostep' 正在导入中，暂不可删除"));
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep"] });
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });

    render(<BookGrid />);
    expect(await screen.findByText("ostep")).toBeInTheDocument();
    await user.hover(screen.getByText("ostep").closest('[data-testid="book-card"]')!);
    fireEvent.click(screen.getByText("删除丛书"));
    await user.click(screen.getByText("确认删除"));

    expect(screen.getByText("ostep")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("正在导入中，暂不可删除");
  });
});
