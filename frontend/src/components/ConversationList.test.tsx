import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { ConversationList } from "./ConversationList";

afterEach(() => vi.restoreAllMocks());

describe("ConversationList", () => {
  it("renders conversation titles and selects one on click", async () => {
    vi.spyOn(client, "listConversations").mockResolvedValue({
      conversations: [{ id: "c1", title: "fork 是什么？", updated_at: "" }],
    });
    const onSelect = vi.fn();

    render(<ConversationList bookId="ostep" selectedId={null} onSelect={onSelect} />);

    const conv = await screen.findByText("fork 是什么？");
    await userEvent.click(conv);
    expect(onSelect).toHaveBeenCalledWith("c1");
  });

  it("creates a new conversation on button click", async () => {
    vi.spyOn(client, "listConversations").mockResolvedValue({ conversations: [] });
    const createSpy = vi.spyOn(client, "createConversation").mockResolvedValue({
      id: "c2", book_id: "ostep", title: "新对话", created_at: "", updated_at: "", turns: [],
    });

    render(<ConversationList bookId="ostep" selectedId={null} onSelect={vi.fn()} />);

    await userEvent.click(screen.getByText("新建对话"));
    expect(createSpy).toHaveBeenCalledWith("ostep");
  });
});
