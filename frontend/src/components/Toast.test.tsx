import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Toast } from "./Toast";

describe("Toast", () => {
  it("shows the message with an alert role by default (error variant)", () => {
    render(<Toast onDismiss={() => {}}>出错了</Toast>);
    expect(screen.getByRole("alert")).toHaveTextContent("出错了");
  });

  it("uses a status role and no error styling for the neutral variant", () => {
    // 回归测试：ImportCompletionToast 迁移到共享 Toast 之后，导入成功的
    // 提示曾经被写死的 role="alert" + 红框 一起套上了错误样式——中性场景
    // 必须换成 status，不能沿用 error 的默认值。
    render(<Toast variant="neutral" onDismiss={() => {}}>导入完成</Toast>);
    expect(screen.getByRole("status")).toHaveTextContent("导入完成");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("calls onDismiss when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(<Toast onDismiss={onDismiss}>出错了</Toast>);

    await user.click(screen.getByLabelText("关闭"));

    expect(onDismiss).toHaveBeenCalledOnce();
  });
});
