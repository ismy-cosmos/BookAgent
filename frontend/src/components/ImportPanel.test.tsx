import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn() }));

import { open } from "@tauri-apps/plugin-dialog";
import * as client from "../api/client";
import type { ProgressResponse } from "../api/types";
import { ImportPanel } from "./ImportPanel";

afterEach(() => vi.restoreAllMocks());

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
});
