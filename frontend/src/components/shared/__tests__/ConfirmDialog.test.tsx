import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";

describe("ConfirmDialog", () => {
  it("shows the message and calls onConfirm when confirmed", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<ConfirmDialog message="确定要删除 'ostep' 吗？" onConfirm={onConfirm} onCancel={onCancel} />);

    expect(screen.getByText("确定要删除 'ostep' 吗？")).toBeInTheDocument();
    await userEvent.click(screen.getByText("确认删除"));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("calls onCancel when cancelled", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<ConfirmDialog message="msg" onConfirm={onConfirm} onCancel={onCancel} />);

    await userEvent.click(screen.getByText("取消"));
    expect(onCancel).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
