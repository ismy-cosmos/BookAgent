import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "./api/client";
import type { ProgressResponse } from "./api/types";
import App from "./App";

afterEach(() => vi.restoreAllMocks());

const IDLE_PROGRESS: ProgressResponse = {
  busy: false, reason: "idle", book_id: null, pause_requested: false,
  progress: null, last_result: null,
};

describe("App", () => {
  it("renders the BookAgent title", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getProgress").mockResolvedValue(IDLE_PROGRESS);

    render(<App />);
    expect(screen.getByText("BookAgent")).toBeInTheDocument();
  });

  it("shows a banner when the backend is unreachable", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("network error"));
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getProgress").mockRejectedValue(new Error("network error"));

    render(<App />);

    expect(await screen.findByText(/服务未响应/)).toBeInTheDocument();
  });

  it("shows the global import bar and jumps to the importing book on click", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
    });
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: ["ostep"] });
    vi.spyOn(client, "getProgress").mockResolvedValue({
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "parsing", current_file: 2, total_files: 5,
                  current_image: null, total_images: null },
      last_result: null,
    });
    vi.spyOn(client, "listStagedFiles").mockResolvedValue({ files: [] });
    vi.spyOn(client, "listFiles").mockResolvedValue({ files: [] });
    vi.spyOn(client, "listConversations").mockResolvedValue({ conversations: [] });

    render(<App />);

    const bar = await screen.findByText(/正在导入《ostep》/);
    expect(bar).toHaveTextContent("解析中 文件 2/5");
    await userEvent.click(bar);

    // 跳到了 ostep 的书页，内嵌导入区可见
    expect(await screen.findByText("待导入")).toBeInTheDocument();
  });
});
