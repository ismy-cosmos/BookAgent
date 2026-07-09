import { render, screen, waitFor } from "@testing-library/react";
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

  it("fetches and displays chunk detail", async () => {
    vi.spyOn(client, "getChunk").mockResolvedValue({
      chunk_id: "c1", content: "fork() 相关内容", source_file: "ch3.pdf",
      element_type: "text", page_start: 42, page_end: 42,
      start_sec: null, end_sec: null, low_confidence: false,
    });

    render(<ChunkDetailModal bookId="ostep" chunkId="c1" onClose={vi.fn()} />);

    await screen.findByText(/fork\(\) 相关内容/);
    expect(screen.getByText(/ch3.pdf/)).toBeInTheDocument();
    expect(screen.getByText(/42/)).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", async () => {
    vi.spyOn(client, "getChunk").mockResolvedValue({
      chunk_id: "c1", content: "text", source_file: "f.pdf",
      element_type: "text", page_start: 1, page_end: 1,
      start_sec: null, end_sec: null, low_confidence: false,
    });
    const onClose = vi.fn();

    render(<ChunkDetailModal bookId="ostep" chunkId="c1" onClose={onClose} />);

    await screen.findByText("text");
    await userEvent.click(screen.getByText("关闭"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
