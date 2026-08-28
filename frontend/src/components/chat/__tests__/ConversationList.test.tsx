import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConversationList } from "@/components/chat/ConversationList";

describe("ConversationList", () => {
  it("renders conversation titles and selects one on click", async () => {
    const onSelect = vi.fn();
    render(
      <ConversationList
        conversations={[{ id: "c1", title: "fork 是什么？", updated_at: "" }]}
        selectedId={null}
        onSelect={onSelect}
        onCreate={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByText("fork 是什么？"));
    expect(onSelect).toHaveBeenCalledWith("c1");
  });

  it("calls onCreate when clicking 新建对话", async () => {
    const onCreate = vi.fn();
    render(
      <ConversationList
        conversations={[]}
        selectedId={null}
        onSelect={vi.fn()}
        onCreate={onCreate}
        onRemove={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "新建对话" }));
    expect(onCreate).toHaveBeenCalledOnce();
  });

  it("calls onRemove without triggering onSelect when clicking 删除", async () => {
    const onSelect = vi.fn();
    const onRemove = vi.fn();
    render(
      <ConversationList
        conversations={[{ id: "c1", title: "t", updated_at: "" }]}
        selectedId={null}
        onSelect={onSelect}
        onCreate={vi.fn()}
        onRemove={onRemove}
      />,
    );

    await userEvent.click(screen.getByText("删除"));
    expect(onRemove).toHaveBeenCalledWith("c1");
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("marks the selected conversation as current", () => {
    render(
      <ConversationList
        conversations={[
          { id: "c1", title: "t1", updated_at: "" },
          { id: "c2", title: "t2", updated_at: "" },
        ]}
        selectedId="c2"
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(screen.getByText("t2").closest("button")).toHaveAttribute("aria-current", "true");
    expect(screen.getByText("t1").closest("button")).toHaveAttribute("aria-current", "false");
  });
});
