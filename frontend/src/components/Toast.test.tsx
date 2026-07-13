import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Toast } from "./Toast";

describe("Toast", () => {
  it("shows the message with an alert role", () => {
    render(<Toast message="出错了" onDismiss={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("出错了");
  });

  it("calls onDismiss when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(<Toast message="出错了" onDismiss={onDismiss} />);

    await user.click(screen.getByLabelText("关闭"));

    expect(onDismiss).toHaveBeenCalledOnce();
  });
});
