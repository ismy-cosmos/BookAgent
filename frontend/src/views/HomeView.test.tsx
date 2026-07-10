import { StrictMode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import type { ProgressResponse } from "../api/types";
import { HomeView } from "./HomeView";

// HomeView installs a real close-requested listener via
// quitConfirmation.installQuitConfirmation, which calls into
// @tauri-apps/api/window's getCurrentWindow() — that throws outside a real
// Tauri webview (no IPC bridge in jsdom). Mock the Tauri module it touches so
// mounting HomeView in tests doesn't produce unhandled rejections.
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: vi.fn(() => ({ onCloseRequested: vi.fn().mockResolvedValue(() => {}) })),
  getAllWindows: vi.fn().mockResolvedValue([]),
}));

import { getAllWindows, getCurrentWindow } from "@tauri-apps/api/window";

afterEach(() => vi.restoreAllMocks());

const IDLE_PROGRESS: ProgressResponse = {
  busy: false, reason: "idle", book_id: null, pause_requested: false,
  progress: null, last_result: null,
};

describe("HomeView", () => {
  it("renders the book grid when reachable", async () => {
    // 内容区不再重复显示"BookAgent"大标题——窗口标题栏已经是"BookAgent"了，
    // 草图确认稿里首页也从没出现过这个重复标题。这里改成验证书架网格本身
    // （新建书入口）确实渲染出来，取代原来断言标题文字的测试。
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getProgress").mockResolvedValue(IDLE_PROGRESS);

    render(<HomeView />);
    expect(await screen.findByLabelText("新建书")).toBeInTheDocument();
  });

  it("shows a banner when the backend is unreachable", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("network error"));
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getProgress").mockRejectedValue(new Error("network error"));

    render(<HomeView />);

    expect(await screen.findByText(/服务未响应/)).toBeInTheDocument();
  });

  it("ends up with exactly one live close-confirmation listener under StrictMode's mount/cleanup/mount", async () => {
    // 回归测试：StrictMode 开发模式下 effect 会 mount→cleanup→再 mount 一遍。
    // installQuitConfirmation 是异步的，如果 cleanup 跑在 promise resolve
    // 之前，第一次注册的监听器永远不会被反注册——两次注册都留下来，一次
    // 关闭窗口会弹两个"确认退出"对话框。这里真实模拟这个异步 gap（用
    // Promise.resolve() 制造一个微任务延迟，对应生产环境里 promise 不会
    // 同步 resolve 的真实情况），断言最终"注册次数－反注册次数"必须是 1。
    let registrations = 0;
    let unregistrations = 0;
    vi.mocked(getCurrentWindow).mockReturnValue({
      onCloseRequested: vi.fn(async () => {
        registrations++;
        await Promise.resolve();
        return () => {
          unregistrations++;
        };
      }),
    } as unknown as ReturnType<typeof getCurrentWindow>);
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getProgress").mockResolvedValue(IDLE_PROGRESS);

    const { unmount } = render(
      <StrictMode>
        <HomeView />
      </StrictMode>,
    );
    await waitFor(() => expect(registrations).toBeGreaterThanOrEqual(2));
    // 挂载稳定后：两次注册里必须有一次被反注册掉了，只剩一个监听器活着
    // （不是两个都活着——那就是这次要修的 bug；也不是两个都被清掉——那样
    // 真正需要生效的监听器反而丢了，关闭窗口时确认框根本不会弹出来）。
    await waitFor(() => expect(registrations - unregistrations).toBe(1));

    unmount();
    await waitFor(() => expect(registrations - unregistrations).toBe(0));
  });

  it("shows an in-app confirm dialog (not the native OS one) when closing while busy, and destroys all windows on confirm", async () => {
    // 换掉原生 confirm() 之后的行为：close-requested 触发时不再调用
    // @tauri-apps/plugin-dialog 的 confirm，而是设置本地状态渲染应用内
    // ConfirmDialog——原生对话框在 Linux/GTK 下会把 title 重复显示成两遍
    // （rfd 库焊死的行为，API 没法关掉），换成应用内弹窗规避这个问题。
    let closeHandler: (event: { preventDefault: () => void }) => void = () => {};
    vi.mocked(getCurrentWindow).mockReturnValue({
      onCloseRequested: vi.fn(async (handler) => {
        closeHandler = handler;
        return () => {};
      }),
    } as unknown as ReturnType<typeof getCurrentWindow>);
    const destroy = vi.fn();
    vi.mocked(getAllWindows).mockResolvedValue([{ destroy }] as never);
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
    });
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getProgress").mockResolvedValue({
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: null, last_result: null,
    });

    const user = userEvent.setup();
    render(<HomeView />);
    await waitFor(() => expect(client.getStatus).toHaveBeenCalled());

    const preventDefault = vi.fn();
    closeHandler({ preventDefault });
    expect(preventDefault).toHaveBeenCalledOnce();
    expect(await screen.findByText("导入正在进行，确定要退出吗？")).toBeInTheDocument();

    await user.click(screen.getByText("确定退出"));
    await waitFor(() => expect(destroy).toHaveBeenCalledOnce());
    expect(screen.queryByText("导入正在进行，确定要退出吗？")).not.toBeInTheDocument();
  });
});
