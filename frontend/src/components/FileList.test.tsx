import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import type { ProgressResponse } from "../api/types";
import { FileList } from "./FileList";

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
    const listFilesSpy = vi.spyOn(client, "listFiles")
      .mockResolvedValueOnce({ files: ["ch01.pdf"] })
      .mockResolvedValueOnce({ files: ["ch01.pdf", "ch02.pdf"] });

    const importing: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "storing", current_file: null, total_files: null,
                  current_image: null, total_images: null, current_filename: null },
      last_result: null,
    };
    const { rerender } = render(<FileList bookId="ostep" progress={importing} />);
    await screen.findByText("ch01.pdf");
    // 挂载时会打两次：useFiles 自己的 mount effect 一次，FileList 这里新加
    // 的"跟 progress 变化刷新"effect 挂载时也会触发一次——跟 ImportPanel.tsx
    // /useStagedFiles 那对既有组合是同一个模式，不是这次新引入的重复。
    const callsAfterMount = listFilesSpy.mock.calls.length;

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
});
