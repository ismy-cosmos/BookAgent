import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NewBookDialog } from "@/components/book/NewBookDialog";

describe("NewBookDialog", () => {
  it("disables 确定 and shows a red warning when the id collides with an existing book", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();

    render(<NewBookDialog existingBookIds={["ostep"]} onCreate={onCreate} onCancel={() => {}} />);
    await user.type(screen.getByLabelText("新书 book_id"), "ostep");

    expect(screen.getByText("书名已存在")).toBeInTheDocument();
    expect(screen.getByText("确定")).toBeDisabled();

    await user.click(screen.getByText("确定"));
    expect(onCreate).not.toHaveBeenCalled();
  });

  it("allows creating once the id no longer collides", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();

    render(<NewBookDialog existingBookIds={["ostep"]} onCreate={onCreate} onCancel={() => {}} />);
    await user.type(screen.getByLabelText("新书 book_id"), "ostep-2");

    expect(screen.queryByText("书名已存在")).not.toBeInTheDocument();
    expect(screen.getByText("确定")).not.toBeDisabled();

    await user.click(screen.getByText("确定"));
    expect(onCreate).toHaveBeenCalledWith("ostep-2");
  });
});
