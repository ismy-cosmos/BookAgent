import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { ChunkDetailModal } from "./ChunkDetailModal";

afterEach(() => vi.restoreAllMocks());

describe("ChunkDetailModal", () => {
  it("renders nothing when chunkId is null", () => {
    const { container } = render(<ChunkDetailModal bookId="ostep" chunkId={null} onClose={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("fetches and displays chunk detail with a page location", async () => {
    vi.spyOn(client, "getChunk").mockResolvedValue({
      chunk_id: "c1", content: "fork() 相关内容", source_file: "ch3.pdf",
      element_type: "text", page_start: 42, page_end: 42,
      start_sec: null, end_sec: null, low_confidence: false,
    });

    render(<ChunkDetailModal bookId="ostep" chunkId="c1" onClose={vi.fn()} />);

    await screen.findByText(/fork\(\) 相关内容/);
    expect(screen.getByText("ch3.pdf")).toBeInTheDocument();
    expect(screen.getByText("第 42 页")).toBeInTheDocument();
  });

  it("displays a time range for audio chunks instead of a page number", async () => {
    vi.spyOn(client, "getChunk").mockResolvedValue({
      chunk_id: "c1", content: "audio 转写内容", source_file: "lecture.mp3",
      element_type: "audio", page_start: null, page_end: null,
      start_sec: 65, end_sec: 130, low_confidence: false,
    });

    render(<ChunkDetailModal bookId="ostep" chunkId="c1" onClose={vi.fn()} />);

    await screen.findByText(/audio 转写内容/);
    expect(screen.getByText("1:05–2:10")).toBeInTheDocument();
  });

  it("shows a dismissible toast when the chunk fetch fails", async () => {
    vi.spyOn(client, "getChunk").mockRejectedValue(new Error("未找到该 chunk: c1"));
    const user = userEvent.setup();

    render(<ChunkDetailModal bookId="ostep" chunkId="c1" onClose={vi.fn()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("未找到该 chunk: c1");
    await user.click(screen.getByLabelText("关闭"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    vi.spyOn(client, "getChunk").mockResolvedValue({
      chunk_id: "c1", content: "text", source_file: "f.pdf",
      element_type: "text", page_start: 1, page_end: 1,
      start_sec: null, end_sec: null, low_confidence: false,
    });
    const onClose = vi.fn();

    render(<ChunkDetailModal bookId="ostep" chunkId="c1" onClose={onClose} />);

    await screen.findByText("text");
    await userEvent.click(screen.getByLabelText("关闭"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when clicking the backdrop outside the card", async () => {
    vi.spyOn(client, "getChunk").mockResolvedValue({
      chunk_id: "c1", content: "text", source_file: "f.pdf",
      element_type: "text", page_start: 1, page_end: 1,
      start_sec: null, end_sec: null, low_confidence: false,
    });
    const onClose = vi.fn();

    render(<ChunkDetailModal bookId="ostep" chunkId="c1" onClose={onClose} />);

    await screen.findByText("text");
    await userEvent.click(screen.getByRole("dialog").parentElement!);
    expect(onClose).toHaveBeenCalledOnce();
  });
});
