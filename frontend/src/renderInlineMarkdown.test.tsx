import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderInlineMarkdown } from "./renderInlineMarkdown";

describe("renderInlineMarkdown", () => {
  it("把 **text** 渲染成真正的加粗元素", () => {
    render(<div>{renderInlineMarkdown("这是**process**的定义")}</div>);
    const strong = screen.getByText("process");
    expect(strong.tagName).toBe("STRONG");
  });

  it("没有 markdown 语法时原样显示文本", () => {
    render(<div>{renderInlineMarkdown("普通文本没有加粗")}</div>);
    expect(screen.getByText("普通文本没有加粗")).toBeInTheDocument();
  });

  it("同一段里多处加粗都能正确渲染", () => {
    render(<div>{renderInlineMarkdown("**A** 和 **B** 都很重要")}</div>);
    expect(screen.getByText("A").tagName).toBe("STRONG");
    expect(screen.getByText("B").tagName).toBe("STRONG");
  });
});
