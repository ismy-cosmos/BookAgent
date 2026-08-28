import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "@/api/client";
import type { ProgressResponse } from "@/api/types";
import { FileList } from "@/components/import/FileList";

afterEach(() => vi.restoreAllMocks());

describe("FileList", () => {
  it("renders file names and initiates removal on delete click", async () => {
    vi.spyOn(client, "listFiles").mockResolvedValue({ files: ["ch01.pdf", "ch02.pdf"] });
    const deleteSpy = vi.spyOn(client, "deleteFile").mockResolvedValue({ deleted_file: "ch01.pdf", book_id: "ostep" });

    render(<FileList bookId="ostep" progress={null} />);

    await screen.findByText("ch01.pdf");

    const deleteButtons = screen.getAllByText("删除");
    await userEvent.click(deleteButtons[0]);

    expect(screen.getByText(/确定要删除 'ch01.pdf'/)).toBeInTheDocument();
    await userEvent.click(screen.getByText("确认删除"));
    expect(deleteSpy).toHaveBeenCalledWith("ostep", "ch01.pdf");
  });

  it("shows empty state when no files", async () => {
    vi.spyOn(client, "listFiles").mockResolvedValue({ files: [] });

    render(<FileList bookId="ostep" progress={null} />);

    await waitFor(() => expect(client.listFiles).toHaveBeenCalled());
    expect(screen.getByText("暂无已导入文件")).toBeInTheDocument();
  });

  it("refreshes the archived file list when an import finishes, without changing bookId", async () => {
    // 回归测试：之前 FileList 完全没接 progress，只在 bookId 变化时拉一次
    // 列表——导入完成后新文件要切书再切回来才能看到。这里模拟同一个
    // ImportView 里 progress 从"导入中"变成"带 last_result 的完成态"，
    // 断言 listFiles 被重新调用、新文件真的渲染出来了。
    // 用一个外部可翻转的标志位驱动 mock 返回值（跟 ImportPanel.test.tsx
    // 的"refreshes staged files..."用的是同一个手法），而不是
    // mockResolvedValueOnce 排队——更贴近真实场景里 listFiles 会被反复
    // 轮询调用的情况。
    let importFinished = false;
    const listFilesSpy = vi.spyOn(client, "listFiles").mockImplementation(async () => ({
      files: importFinished ? ["ch01.pdf", "ch02.pdf"] : ["ch01.pdf"],
    }));

    const importing: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "storing", current_file: null, total_files: null,
                  current_image: null, total_images: null, current_filename: null },
      last_result: null,
    };
    const { rerender } = render(<FileList bookId="ostep" progress={importing} />);
    await screen.findByText("ch01.pdf");
    const callsAfterMount = listFilesSpy.mock.calls.length;
    importFinished = true;

    const finished: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null,
      last_result: { book_id: "ostep", total_chunks: 9, aborted_early: false,
                     failures: [], not_attempted: [] },
    };
    rerender(<FileList bookId="ostep" progress={finished} />);

    await waitFor(() =>
      expect(listFilesSpy.mock.calls.length).toBeGreaterThan(callsAfterMount));
    expect(await screen.findByText("ch02.pdf")).toBeInTheDocument();
  });

  it("does not refresh when a different book's busy state changes", async () => {
    const listFilesSpy = vi.spyOn(client, "listFiles").mockResolvedValue({ files: ["ch01.pdf"] });

    const otherBookAnswering: ProgressResponse = {
      busy: true, reason: "answering", book_id: "other-book", pause_requested: false,
      progress: null, last_result: null,
    };
    const { rerender } = render(<FileList bookId="ostep" progress={otherBookAnswering} />);
    await screen.findByText("ch01.pdf");
    const callsAfterMount = listFilesSpy.mock.calls.length;

    const otherBookIdle: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null, last_result: null,
    };
    rerender(<FileList bookId="ostep" progress={otherBookIdle} />);

    // 没有"会发生"的信号可以 waitFor，这里等一小段时间确认真的没有发生
    // 多余的调用——比现有测试断言"发生"更弱的负面断言只能这样写。
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(listFilesSpy.mock.calls.length).toBe(callsAfterMount);
  });
});
