import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProgressResponse } from "../api/types";
import { GlobalImportCapsule } from "./GlobalImportCapsule";

function busyProgress(): ProgressResponse {
  return {
    busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
    progress: { stage: "parsing", current_file: 1, total_files: 3,
                current_image: null, total_images: null, current_filename: "ch01.pdf" },
    last_result: null,
  };
}

describe("GlobalImportCapsule", () => {
  it("renders nothing when not busy", () => {
    render(<GlobalImportCapsule progress={null} onPause={() => {}} />);
    expect(screen.queryByTestId("import-capsule")).not.toBeInTheDocument();
  });

  it("shows collapsed pill with percentage-ish stage text when busy", () => {
    render(<GlobalImportCapsule progress={busyProgress()} onPause={() => {}} />);
    expect(screen.getByTestId("import-capsule")).toBeInTheDocument();
    expect(screen.queryByText(/ostep/)).not.toBeInTheDocument();
  });

  it("collapsed pill labels the percentage with the current stage, not a bare number", () => {
    // 回归测试：之前折叠态只显示裸的"{percent}%"——阶段1文件全解析完时会
    // 显示"100%"，让人误以为整个导入都完成了，实际只是第一阶段。现在必须
    // 带上阶段名，不能是纯数字。
    render(<GlobalImportCapsule progress={busyProgress()} onPause={() => {}} />);
    expect(screen.getByText("解析 0%")).toBeInTheDocument();
    expect(screen.queryByText(/^100%$/)).not.toBeInTheDocument();
  });

  it("shows 0%, not 100%, while the only file is still being parsed", () => {
    // 回归测试：current_file 是后端在开始解析某个文件*之前*就发出的
    // 1-indexed"当前在第几个"指针，不是完成计数（scripts/ingest.py 解析
    // 循环里 on_progress 在 _parse_file 之前调用）。total_files=1 时若不做
    // -1 修正，current_file=1/total_files=1 直接读成 100%，会在唯一那个
    // 文件明明还在解析的时候就显示"已完成"。
    const singleFileJustStarted: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "parsing", current_file: 1, total_files: 1,
                  current_image: null, total_images: null, current_filename: "only.pdf" },
      last_result: null,
    };
    render(<GlobalImportCapsule progress={singleFileJustStarted} onPause={() => {}} />);
    expect(screen.getByText("解析 0%")).toBeInTheDocument();
  });

  it("collapsed pill shows '存储中' without a misleading percentage during the storing stage", () => {
    const storing: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "storing", current_file: null, total_files: null,
                  current_image: null, total_images: null, current_filename: null },
      last_result: null,
    };
    render(<GlobalImportCapsule progress={storing} onPause={() => {}} />);
    expect(screen.getByText("存储中")).toBeInTheDocument();
  });

  it("expanded view renders three independent stage segments, not one merged bar", async () => {
    // 回归测试：分段进度条——解析阶段完成 1/3 只应该填满"解析"这一段，
    // "图片"和"存储"两段必须留空，不能借用总百分比填满整条。
    const user = userEvent.setup();
    render(<GlobalImportCapsule progress={busyProgress()} onPause={() => {}} />);
    await user.click(screen.getByTestId("import-capsule"));

    expect(screen.getByTestId("progress-segment-parsing")).toHaveStyle({ width: "0%" });
    expect(screen.getByTestId("progress-segment-vlm")).toHaveStyle({ width: "0%" });
    expect(screen.getByTestId("progress-segment-storing")).toHaveStyle({ width: "0%" });
  });

  it("marks earlier stages as fully filled once the task has moved past them", async () => {
    const user = userEvent.setup();
    const inVlmStage: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "vlm", current_file: null, total_files: null,
                  current_image: 4, total_images: 10, current_filename: null },
      last_result: null,
    };
    render(<GlobalImportCapsule progress={inVlmStage} onPause={() => {}} />);
    await user.click(screen.getByTestId("import-capsule"));

    expect(screen.getByTestId("progress-segment-parsing")).toHaveStyle({ width: "100%" });
    expect(screen.getByTestId("progress-segment-vlm")).toHaveStyle({ width: "30%" });
    expect(screen.getByTestId("progress-segment-storing")).toHaveStyle({ width: "0%" });
  });

  it("shows an indeterminate animation for the storing segment instead of a fake percentage", async () => {
    const user = userEvent.setup();
    const storing: ProgressResponse = {
      busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
      progress: { stage: "storing", current_file: null, total_files: null,
                  current_image: null, total_images: null, current_filename: null },
      last_result: null,
    };
    render(<GlobalImportCapsule progress={storing} onPause={() => {}} />);
    await user.click(screen.getByTestId("import-capsule"));

    expect(screen.getByTestId("progress-segment-parsing")).toHaveStyle({ width: "100%" });
    expect(screen.getByTestId("progress-segment-vlm")).toHaveStyle({ width: "100%" });
    const storingSegment = screen.getByTestId("progress-segment-storing");
    expect(storingSegment.style.width).toBe("");
  });

  it("expands to show book id, stage text and a pause button on click", async () => {
    const user = userEvent.setup();
    render(<GlobalImportCapsule progress={busyProgress()} onPause={() => {}} />);

    await user.click(screen.getByTestId("import-capsule"));

    expect(screen.getByText(/ostep/)).toBeInTheDocument();
    expect(screen.getByText(/解析中/)).toBeInTheDocument();
    expect(screen.getByText("暂停")).toBeInTheDocument();
  });

  it("collapses again on a second click", async () => {
    const user = userEvent.setup();
    render(<GlobalImportCapsule progress={busyProgress()} onPause={() => {}} />);

    const capsule = screen.getByTestId("import-capsule");
    await user.click(capsule);
    expect(screen.getByText("暂停")).toBeInTheDocument();
    await user.click(capsule);
    expect(screen.queryByText("暂停")).not.toBeInTheDocument();
  });

  it("clicking 暂停 calls onPause", async () => {
    const user = userEvent.setup();
    const onPause = vi.fn();
    render(<GlobalImportCapsule progress={busyProgress()} onPause={onPause} />);

    await user.click(screen.getByTestId("import-capsule"));
    await user.click(screen.getByText("暂停"));

    expect(onPause).toHaveBeenCalledOnce();
  });
});
