import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "./api/client";
import App from "./App";

afterEach(() => vi.restoreAllMocks());

describe("App", () => {
  it("renders the BookAgent title", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });

    render(<App />);
    expect(screen.getByText("BookAgent")).toBeInTheDocument();
  });

  it("shows a banner when the backend is unreachable", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("network error"));
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });

    render(<App />);

    expect(await screen.findByText(/服务未响应/)).toBeInTheDocument();
  });
});
