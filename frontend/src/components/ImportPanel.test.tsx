import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn() }));
vi.mock("@tauri-apps/api/path", () => ({
  dirname: vi.fn(async (p: string) => p.substring(0, p.lastIndexOf("/"))),
}));

import { open } from "@tauri-apps/plugin-dialog";
import * as client from "../api/client";
import type { ProgressResponse } from "../api/types";
import { ImportPanel } from "./ImportPanel";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

const IDLE_PROGRESS: ProgressResponse = {
  busy: false, reason: "idle", book_id: null, pause_requested: false,
  progress: null, last_result: null,
};

describe("ImportPanel", () => {
  it("renders staged files and removes one on ×", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/data/ch01.pdf"] });
    const removeSpy = vi.spyOn(client, "removeStagedFile").mockResolvedValue({ files: [] });

    render(<ImportPanel bookId="ostep" progress={IDLE_PROGRESS} />);

    await screen.findByText("/data/ch01.pdf");
    await userEvent.click(screen.getByLabelText("移除 /data/ch01.pdf"));
    expect(removeSpy).toHaveBeenCalledWith("ostep", "/data/ch01.pdf");
  });

  it("opens the native picker and adds every picked file", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    const addSpy = vi.spyOn(client, "addStagedFile")
      .mockResolvedValueOnce({ files: ["/a.pdf"] })
      .mockResolvedValueOnce({ files: ["/a.pdf", "/b.epub"] });
    vi.mocked(open).mockResolvedValue(["/a.pdf", "/b.epub"]);

    render(<ImportPanel bookId="ostep" progress={IDLE_PROGRESS} />);
    await userEvent.click(screen.getByText("添加文件"));

    await waitFor(() => expect(addSpy).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("/b.epub")).toBeInTheDocument();
  });

  it("shows a dismissible toast when adding a staged file is rejected by the backend", async () => {
    // 之前这条错误路径（useStagedFiles 的 error）完全没测过——比如选了不
    // 支持的格式，后端 400 拒绝。
    const user = userEvent.setup();
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    vi.spyOn(client, "addStagedFile")
      .mockRejectedValue(new Error("不支持的文件类型：.txt"));
    vi.mocked(open).mockResolvedValue(["/notes.txt"]);

    render(<ImportPanel bookId="ostep" progress={IDLE_PROGRESS} />);
    await user.click(screen.getByText("添加文件"));

    expect(await screen.findByRole("alert")).toHaveTextContent("不支持的文件类型：.txt");
    await user.click(screen.getByLabelText("关闭"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a dismissible toast when submitting the import is rejected", async () => {
    // actionError 路径（handleSubmit 的 catch）之前也完全没测过。
    const user = userEvent.setup();
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    vi.spyOn(client, "submitImport")
      .mockRejectedValue(new Error("待导入文件列表为空，没有可提交的内容"));

    render(<ImportPanel bookId="ostep" progress={IDLE_PROGRESS} />);
    await screen.findByText("/a.pdf");
    await user.click(screen.getByText("开始导入"));

    expect(await screen.findByRole("alert"))
      .toHaveTextContent("待导入文件列表为空，没有可提交的内容");
    await user.click(screen.getByLabelText("关闭"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("opens the picker in the last-used directory and remembers the new one", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    vi.spyOn(client, "addStagedFile").mockResolvedValue({ files: ["/data/ch01.pdf"] });
    localStorage.setItem("bookagent:lastImportDir", "/old/dir");
    vi.mocked(open).mockResolvedValue(["/data/ch01.pdf"]);

    render(<ImportPanel bookId="ostep" progress={IDLE_PROGRESS} />);
    await userEvent.click(screen.getByText("添加文件"));

    expect(open).toHaveBeenCalledWith(
      expect.objectContaining({ defaultPath: "/old/dir" }),
    );
    await waitFor(() =>
      expect(localStorage.getItem("bookagent:lastImportDir")).toBe("/data"),
    );
  });

  it("disables submit when the staged list is empty", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });

    render(<ImportPanel bookId="ostep" progress={IDLE_PROGRESS} />);

    await waitFor(() => expect(client.listStagedFiles).toHaveBeenCalled());
    expect(screen.getByText("开始导入")).toBeDisabled();
  });

  it("submits the import when files are staged", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    const submitSpy = vi.spyOn(client, "submitImport")
      .mockResolvedValue({ task_id: "t1", file_count: 1 });

    render(<ImportPanel bookId="ostep" progress={IDLE_PROGRESS} />);

    await screen.findByText("/a.pdf");
    await userEvent.click(screen.getByText("开始导入"));
    expect(submitSpy).toHaveBeenCalledWith("ostep");
  });

  it("shows stage progress and offers pause while importing this book", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    vi.spyOn(client, "pauseImport").mockResolvedValue({
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: true,
    });
    const busy: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "vlm", current_file: 3, total_files: 3,
                  current_image: 7, total_images: 40 },
      last_result: null,
    };

    render(<ImportPanel bookId="ostep" progress={busy} />);

    expect(await screen.findByText("图片描述 7/40")).toBeInTheDocument();
    await userEvent.click(screen.getByText("暂停"));
    expect(client.pauseImport).toHaveBeenCalled();
  });

  it("shows result summary with expandable failure details", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    const done: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null,
      last_result: {
        book_id: "ostep", total_chunks: 120, aborted_early: false,
        failures: [{ file: "/bad.pdf", error_type: "RuntimeError",
                     error_message: "boom", timestamp: "2026-07-09T00:00:00" }],
        not_attempted: [],
      },
    };

    render(<ImportPanel bookId="ostep" progress={done} />);

    expect(await screen.findByText(/导入完成：入库 120 块/)).toBeInTheDocument();
    await userEvent.click(screen.getByText("查看失败详情"));
    expect(screen.getByText(/\/bad\.pdf：boom/)).toBeInTheDocument();
  });

  it("shows the whole-task error from last_result", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    const failed: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null,
      last_result: { book_id: "ostep", error: "RuntimeError: manifest 损坏" },
    };

    render(<ImportPanel bookId="ostep" progress={failed} />);

    expect(await screen.findByText(/导入失败：RuntimeError: manifest 损坏/)).toBeInTheDocument();
  });

  it("shows a disabled '正在暂停…' button while the pause is taking effect", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    const pausing: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: true,
      progress: { stage: "parsing", current_file: 2, total_files: 5,
                  current_image: null, total_images: null },
      last_result: null,
    };

    render(<ImportPanel bookId="ostep" progress={pausing} />);

    expect(await screen.findByText("正在暂停…")).toBeDisabled();
    // 暂停按钮不应该跟"正在暂停…"同时出现
    expect(screen.queryByText("暂停")).toBeNull();
  });

  it("暂停后（不管是不是这本书自己触发的）没有'恢复'这回事，直接退回正常待导入态", async () => {
    // 暂停是决定性动作：当前任务收尾、排队全部取消，不存在"恢复"——
    // 界面上就应该跟这本书从来没排过队/没暂停过一样，正常显示添加文件+
    // 开始导入，用户想继续导入自己重新点。
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    const paused: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: true,
      progress: null, last_result: null,
    };

    render(<ImportPanel bookId="ostep" progress={paused} />);

    expect(await screen.findByText("开始导入")).toBeInTheDocument();
    expect(screen.queryByText("已暂停")).not.toBeInTheDocument();
    expect(screen.queryByText("恢复")).not.toBeInTheDocument();
  });

  it("排队中的书如果被全局暂停顺手取消了，本地状态跟着清掉，退回正常待导入态", async () => {
    // 不一定是这本书自己点的暂停——可能是另一本正在导入的书那边点的，
    // 但 request_pause() 会把所有排队中的任务（包括这本）一起取消。
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    vi.spyOn(client, "submitImport").mockResolvedValue({ task_id: "t-queued", file_count: 1 });
    const busyElsewhere: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "other-book", pause_requested: false,
      progress: { stage: "parsing", current_file: 1, total_files: 2,
                  current_image: null, total_images: null, current_filename: "x.pdf" },
      last_result: null,
    };

    const { rerender } = render(<ImportPanel bookId="ostep" progress={busyElsewhere} />);
    await screen.findByText("/a.pdf");
    await userEvent.click(screen.getByText("开始导入"));
    await screen.findByText("取消排队");

    const paused: ProgressResponse = { ...busyElsewhere, pause_requested: true };
    rerender(<ImportPanel bookId="ostep" progress={paused} />);

    expect(await screen.findByText("添加文件")).toBeInTheDocument();
    expect(screen.queryByText("取消排队")).not.toBeInTheDocument();
  });

  it("refreshes staged files when an import finishes without ever observing busy:true", async () => {
    // 导入耗时短于 2 秒轮询间隔时，前端可能完全错过 busy:true 那个中间态，
    // progress 从"导入前"直接跳到"导入后"，busy 全程都是 false。
    let fileImported = false;
    const listSpy = vi.spyOn(client, "listStagedFiles")
      .mockImplementation(async () => ({ files: fileImported ? [] : ["/a.pdf"] }));

    const { rerender } = render(<ImportPanel bookId="ostep" progress={IDLE_PROGRESS} />);
    await screen.findByText("/a.pdf");
    const callsBeforeCompletion = listSpy.mock.calls.length;
    fileImported = true;

    const justFinished: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null,
      last_result: { book_id: "ostep", total_chunks: 3, aborted_early: false,
                     failures: [], not_attempted: [] },
    };
    rerender(<ImportPanel bookId="ostep" progress={justFinished} />);

    await waitFor(() =>
      expect(listSpy.mock.calls.length).toBeGreaterThan(callsBeforeCompletion),
    );
    await waitFor(() => expect(screen.queryByText("/a.pdf")).toBeNull());
  });

  it("auto-dismisses the completion toast even while re-rendering from polling", async () => {
    // 回归测试：之前 onDismiss 是每次渲染新建的内联函数，ImportCompletionToast
    // 内部的自动消失计时器把它当 useEffect 依赖，随每次轮询重渲染反复清掉重
    // 开，永远攒不够 6 秒。这里用 rerender 模拟轮询，验证计时器真的能跑完。
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    const done: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null,
      last_result: { book_id: "ostep", total_chunks: 3, aborted_early: false,
                     failures: [], not_attempted: [] },
    };

    const { rerender } = render(<ImportPanel bookId="ostep" progress={done} />);
    expect(await screen.findByText(/导入完成：入库 3 块/)).toBeInTheDocument();

    // 模拟轮询：每 500ms 重渲染一次同样的 progress，持续 6 秒
    for (let i = 0; i < 12; i++) {
      await vi.advanceTimersByTimeAsync(500);
      rerender(<ImportPanel bookId="ostep" progress={{ ...done }} />);
    }

    expect(screen.queryByText(/导入完成：入库 3 块/)).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("does not re-show a completion toast already dismissed in a previous mount of the same book", async () => {
    // 回归测试：之前"已经弹过"的记录只存在内存 ref 里，窗口关闭重开=组件
    // 重新 mount，内存态丢失，同一份 last_result 会再弹一次。
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    const done: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null,
      last_result: { book_id: "ostep", total_chunks: 3, aborted_early: false,
                     failures: [], not_attempted: [] },
    };

    const { unmount } = render(<ImportPanel bookId="ostep" progress={done} />);
    expect(await screen.findByText(/导入完成：入库 3 块/)).toBeInTheDocument();
    unmount();

    render(<ImportPanel bookId="ostep" progress={done} />);
    await waitFor(() => expect(client.listStagedFiles).toHaveBeenCalled());
    expect(screen.queryByText(/导入完成：入库 3 块/)).not.toBeInTheDocument();
  });

  it("still shows a genuinely new completion result for the same book after a remount", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    const first: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null,
      last_result: { book_id: "ostep", total_chunks: 3, aborted_early: false,
                     failures: [], not_attempted: [] },
    };
    const second: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null,
      last_result: { book_id: "ostep", total_chunks: 9, aborted_early: false,
                     failures: [], not_attempted: [] },
    };

    const { unmount } = render(<ImportPanel bookId="ostep" progress={first} />);
    expect(await screen.findByText(/导入完成：入库 3 块/)).toBeInTheDocument();
    unmount();

    render(<ImportPanel bookId="ostep" progress={second} />);
    expect(await screen.findByText(/导入完成：入库 9 块/)).toBeInTheDocument();
  });

  it("offers cancel for a task queued behind another book and cancels it", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    vi.spyOn(client, "submitImport").mockResolvedValue({ task_id: "t-queued", file_count: 1 });
    const cancelSpy = vi.spyOn(client, "cancelImport").mockResolvedValue({ cancelled: "t-queued" });
    const busyElsewhere: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "other-book", pause_requested: false,
      progress: { stage: "parsing", current_file: 1, total_files: 2,
                  current_image: null, total_images: null },
      last_result: null,
    };

    render(<ImportPanel bookId="ostep" progress={busyElsewhere} />);

    await screen.findByText("/a.pdf");
    await userEvent.click(screen.getByText("开始导入"));

    await userEvent.click(await screen.findByText("取消排队"));
    expect(cancelSpy).toHaveBeenCalledWith("t-queued");
  });

  it("正在导入时移除按钮变灰显示'导入中'，添加文件也被禁用", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    const importing: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "parsing", current_file: 1, total_files: 1,
                  current_image: null, total_images: null, current_filename: "a.pdf" },
      last_result: null,
    };

    render(<ImportPanel bookId="ostep" progress={importing} />);

    expect(await screen.findByText("导入中")).toBeDisabled();
    expect(screen.getByText("添加文件")).toBeDisabled();
  });

  it("排队中整批只读，只有取消排队可点", async () => {
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: ["/a.pdf"] });
    vi.spyOn(client, "submitImport").mockResolvedValue({ task_id: "t-queued", file_count: 1 });
    const busyElsewhere: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "other-book", pause_requested: false,
      progress: { stage: "parsing", current_file: 1, total_files: 2,
                  current_image: null, total_images: null, current_filename: "x.pdf" },
      last_result: null,
    };

    render(<ImportPanel bookId="ostep" progress={busyElsewhere} />);
    await screen.findByText("/a.pdf");
    await userEvent.click(screen.getByText("开始导入"));
    await screen.findByText("取消排队");

    expect(screen.queryByText("添加文件")).not.toBeInTheDocument();
    expect(screen.queryByText("移除")).not.toBeInTheDocument();
    expect(screen.queryByText("开始导入")).not.toBeInTheDocument();
    expect(screen.getByText("取消排队")).not.toBeDisabled();
  });

});
