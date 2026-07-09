import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProgressResponse } from "../api/types";
import { ImportStatusBar } from "./ImportStatusBar";

describe("ImportStatusBar", () => {
  it("renders nothing when idle", () => {
    const idle: ProgressResponse = {
      busy: false, reason: "idle", book_id: null, pause_requested: false,
      progress: null, last_result: null,
    };
    const { container } = render(<ImportStatusBar progress={idle} onJumpToBook={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows book and stage while importing, jumps to the book on click", async () => {
    const busy: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "parsing", current_file: 2, total_files: 5,
                  current_image: null, total_images: null },
      last_result: null,
    };
    const onJumpToBook = vi.fn();

    render(<ImportStatusBar progress={busy} onJumpToBook={onJumpToBook} />);

    const bar = screen.getByText(/正在导入《ostep》/);
    expect(bar).toHaveTextContent("解析中 文件 2/5");
    await userEvent.click(bar);
    expect(onJumpToBook).toHaveBeenCalledWith("ostep");
  });

  it("appends a pausing hint while the pause is taking effect", () => {
    const pausing: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: true,
      progress: { stage: "vlm", current_file: 3, total_files: 3,
                  current_image: 7, total_images: 40 },
      last_result: null,
    };

    render(<ImportStatusBar progress={pausing} onJumpToBook={vi.fn()} />);

    expect(screen.getByText(/正在暂停…/)).toBeInTheDocument();
  });
});
