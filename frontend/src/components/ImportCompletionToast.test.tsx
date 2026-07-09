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
});
