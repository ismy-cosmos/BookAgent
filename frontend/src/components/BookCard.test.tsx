import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BookCard } from "./BookCard";

vi.mock("../windowManager", () => ({
  openOrFocusWindow: vi.fn(),
}));
import { openOrFocusWindow } from "../windowManager";

describe("BookCard", () => {
  it("shows book name always, action buttons only on hover", async () => {
    const user = userEvent.setup();
    render(
      <BookCard bookId="ostep" busy={false} importing={false}
                onRemove={() => {}} onRename={async () => {}} />,
    );

    expect(screen.getByText("ostep")).toBeInTheDocument();
    expect(screen.queryByText("导入文件")).not.toBeInTheDocument();

    await user.hover(screen.getByTestId("book-card"));

    expect(screen.getByText("导入文件")).toBeInTheDocument();
    expect(screen.getByText("开始对话")).toBeInTheDocument();
    expect(screen.getByText("删除丛书")).toBeInTheDocument();
  });

  it("clicking 导入文件 opens the import window for this book", async () => {
    const user = userEvent.setup();
    render(
      <BookCard bookId="ostep" busy={false} importing={false}
                onRemove={() => {}} onRename={async () => {}} />,
    );
    await user.hover(screen.getByTestId("book-card"));
    // fireEvent.click (not userEvent.click): userEvent simulates a realistic
    // pointer path for the click, which in jsdom fires mouseleave on the
    // hover-tracked card ancestor before the button's own click handler runs
    // — unmounting the button (conditionally rendered on hover) out from
    // under its own click. A raw click event has no such pointer path.
    fireEvent.click(screen.getByText("导入文件"));

    expect(openOrFocusWindow).toHaveBeenCalledWith("import", "ostep", "ostep");
  });

  it("clicking 开始对话 opens the chat window for this book", async () => {
    const user = userEvent.setup();
    render(
      <BookCard bookId="ostep" busy={false} importing={false}
                onRemove={() => {}} onRename={async () => {}} />,
    );
    await user.hover(screen.getByTestId("book-card"));
    fireEvent.click(screen.getByText("开始对话"));

    expect(openOrFocusWindow).toHaveBeenCalledWith("chat", "ostep", "ostep");
  });

  it("disables 开始对话 when busy is true, even for a different book", async () => {
    const user = userEvent.setup();
    render(
      <BookCard bookId="ostep" busy={true} importing={false}
                onRemove={() => {}} onRename={async () => {}} />,
    );
    await user.hover(screen.getByTestId("book-card"));

    expect(screen.getByText("开始对话")).toBeDisabled();
    expect(screen.getByText("导入文件")).not.toBeDisabled();
  });

  it("disables 删除丛书 when this book is importing", async () => {
    const user = userEvent.setup();
    render(
      <BookCard bookId="ostep" busy={true} importing={true}
                onRemove={() => {}} onRename={async () => {}} />,
    );
    await user.hover(screen.getByTestId("book-card"));

    expect(screen.getByText("删除丛书")).toBeDisabled();
  });

  it("keeps 删除丛书 enabled when a different book is busy, not this one", async () => {
    // book_has_pending_or_active_task 是按 book_id 精确判断的，不是全局
    // busy 就该拦——只有这本书自己在导入才该拦删除，别的书忙不该连累它。
    const user = userEvent.setup();
    render(
      <BookCard bookId="ostep" busy={true} importing={false}
                onRemove={() => {}} onRename={async () => {}} />,
    );
    await user.hover(screen.getByTestId("book-card"));

    expect(screen.getByText("删除丛书")).not.toBeDisabled();
  });

  it("shows an importing badge when importing is true", () => {
    render(
      <BookCard bookId="ostep" busy={true} importing={true}
                onRemove={() => {}} onRename={async () => {}} />,
    );
    expect(screen.getByText("导入中…")).toBeInTheDocument();
  });

  it("clicking 删除丛书 then confirming calls onRemove", async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn();
    render(
      <BookCard bookId="ostep" busy={false} importing={false}
                onRemove={onRemove} onRename={async () => {}} />,
    );
    await user.hover(screen.getByTestId("book-card"));
    fireEvent.click(screen.getByText("删除丛书"));
    await user.click(screen.getByText("确认删除"));

    expect(onRemove).toHaveBeenCalledWith("ostep");
  });

  it("double-clicking the name enters edit mode and Enter saves", async () => {
    const onRename = vi.fn().mockResolvedValue(undefined);
    render(
      <BookCard bookId="ostep" busy={false} importing={false}
                onRemove={() => {}} onRename={onRename} />,
    );

    fireEvent.doubleClick(screen.getByText("ostep"));
    const input = screen.getByDisplayValue("ostep");
    fireEvent.change(input, { target: { value: "ostep-v2" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onRename).toHaveBeenCalledWith("ostep", "ostep-v2");
  });

  it("reverts to the old name when the backend rejects a rename to a name that already exists", async () => {
    // 改名不做实时查重 UI（跟"新建书"不一样）——直接交给后端判断，
    // 冲突时改名失败，输入框回退到原名即可。
    const onRename = vi.fn().mockRejectedValue(new Error("book_id 'civil-law' 已存在"));
    render(
      <BookCard bookId="ostep" busy={false} importing={false}
                onRemove={() => {}} onRename={onRename} />,
    );

    fireEvent.doubleClick(screen.getByText("ostep"));
    const input = screen.getByDisplayValue("ostep");
    fireEvent.change(input, { target: { value: "civil-law" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onRename).toHaveBeenCalledWith("ostep", "civil-law");
    expect(await screen.findByText("ostep")).toBeInTheDocument();
    expect(screen.queryByText("civil-law")).not.toBeInTheDocument();
  });
});
