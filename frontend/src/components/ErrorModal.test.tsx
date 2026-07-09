import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ErrorModal } from "./ErrorModal";

describe("ErrorModal", () => {
  it("renders nothing when message is null", () => {
    const { container } = render(<ErrorModal message={null} onDismiss={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the message and calls onDismiss when clicked", async () => {
    const onDismiss = vi.fn();
    render(<ErrorModal message="无法连接本地模型服务" onDismiss={onDismiss} />);

    expect(screen.getByText("无法连接本地模型服务")).toBeInTheDocument();
    await userEvent.click(screen.getByText("知道了"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});
