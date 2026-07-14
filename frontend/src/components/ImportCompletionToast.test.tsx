import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { LastResult } from "../api/types";
import { ImportCompletionToast } from "./ImportCompletionToast";

describe("ImportCompletionToast", () => {
  it("shows result summary with expandable failure details", async () => {
    const user = userEvent.setup();
    const result: LastResult = {
      book_id: "ostep", total_chunks: 120, aborted_early: false,
      failures: [{ file: "/bad.pdf", error_type: "RuntimeError",
                   error_message: "boom", timestamp: "2026-07-09T00:00:00" }],
      not_attempted: [],
    };

    render(<ImportCompletionToast result={result} onDismiss={() => {}} />);

    expect(screen.getByText(/导入完成：入库 120 块/)).toBeInTheDocument();
    await user.click(screen.getByText("查看失败详情"));
    expect(screen.getByText(/\/bad\.pdf：boom/)).toBeInTheDocument();
  });

  it("shows the whole-task error", () => {
    const result: LastResult = { book_id: "ostep", error: "RuntimeError: manifest 损坏" };

    render(<ImportCompletionToast result={result} onDismiss={() => {}} />);

    expect(screen.getByText(/导入失败：RuntimeError: manifest 损坏/)).toBeInTheDocument();
  });

  it("uses a neutral status role, not an error alert, when the import actually succeeded", () => {
    // 回归测试：迁移到共享 Toast 组件后一度把 role 写死成 alert、边框写死成
    // 红色——哪怕导入 100% 成功也会套上错误样式/用"警报"语义读给屏幕阅读器。
    // 只有 result.error 真的有值时才该是 error 语义。
    const result: LastResult = {
      book_id: "ostep", total_chunks: 120, aborted_early: false,
      failures: [], not_attempted: [],
    };

    render(<ImportCompletionToast result={result} onDismiss={() => {}} />);

    expect(screen.getByRole("status")).toHaveTextContent(/导入完成/);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("uses an error alert role when the whole task failed", () => {
    const result: LastResult = { book_id: "ostep", error: "RuntimeError: manifest 损坏" };

    render(<ImportCompletionToast result={result} onDismiss={() => {}} />);

    expect(screen.getByRole("alert")).toHaveTextContent(/导入失败/);
  });

  it("auto-dismisses after a few seconds", () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    const result: LastResult = { book_id: "ostep", total_chunks: 3, failures: [], not_attempted: [] };

    render(<ImportCompletionToast result={result} onDismiss={onDismiss} />);
    expect(onDismiss).not.toHaveBeenCalled();

    vi.advanceTimersByTime(6000);
    expect(onDismiss).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });

  it("dismisses immediately when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    const result: LastResult = { book_id: "ostep", total_chunks: 3, failures: [], not_attempted: [] };

    render(<ImportCompletionToast result={result} onDismiss={onDismiss} />);
    await user.click(screen.getByLabelText("关闭"));

    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("暂停打断时显示'已暂停'而不是'导入完成'，且带上阶段快照算出的未处理数", () => {
    // 暂停不是失败也不是成功——用"导入完成：入库 0 块"会跟真失败长得
    // 一样，用户没法区分"我主动暂停的"和"这次导入啥也没干成"。
    // 剩余数来自 pausedAtProgress 快照，不是 not_attempted.length：
    // not_attempted 在阶段2中断时存的是"文件"，但暂停实际打断的可能是"图片"。
    const result: LastResult = {
      book_id: "ostep", total_chunks: 0, aborted_early: true,
      failures: [], not_attempted: ["ch02.pdf", "ch03.pdf"],
    };
    // current_file=3, total_files=4 → remaining = 4 - (3-1) = 2 个文件未解析
    const pausedAtProgress = {
      stage: "parsing" as const,
      current_file: 3, total_files: 4,
      current_image: null, total_images: null,
    };

    render(<ImportCompletionToast result={result} pausedAtProgress={pausedAtProgress} onDismiss={() => {}} />);

    expect(screen.getByText(/已暂停/)).toBeInTheDocument();
    expect(screen.getByText(/还有 2 个文件未解析/)).toBeInTheDocument();
    expect(screen.queryByText(/导入完成/)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("暂停弹窗不自动关闭——用户必须手动点关闭才消失", () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    const result: LastResult = {
      book_id: "ostep", total_chunks: 0, aborted_early: true,
      failures: [], not_attempted: ["ch02.pdf"],
    };

    render(<ImportCompletionToast result={result} onDismiss={onDismiss} />);
    vi.advanceTimersByTime(60000);  // 远超正常的 6 秒自动消失时间

    expect(onDismiss).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
