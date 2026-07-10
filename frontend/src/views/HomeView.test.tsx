import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import type { ProgressResponse } from "../api/types";
import { HomeView } from "./HomeView";

// HomeView installs a real close-requested listener via
// quitConfirmation.installQuitConfirmation, which calls into
// @tauri-apps/api/window's getCurrentWindow() — that throws outside a real
// Tauri webview (no IPC bridge in jsdom). Mock both Tauri modules it touches
// so mounting HomeView in tests doesn't produce unhandled rejections.
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ onCloseRequested: vi.fn().mockResolvedValue(() => {}) }),
  getAllWindows: vi.fn().mockResolvedValue([]),
}));
vi.mock("@tauri-apps/plugin-dialog", () => ({
  confirm: vi.fn().mockResolvedValue(false),
}));

afterEach(() => vi.restoreAllMocks());

const IDLE_PROGRESS: ProgressResponse = {
  busy: false, reason: "idle", book_id: null, pause_requested: false,
  progress: null, last_result: null,
};

describe("HomeView", () => {
  it("renders the BookAgent title", async () => {
    vi.spyOn(client, "getStatus").mockResolvedValue({
      busy: false, reason: "idle", book_id: null, pause_requested: false,
    });
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getProgress").mockResolvedValue(IDLE_PROGRESS);

    render(<HomeView />);
    expect(screen.getByText("BookAgent")).toBeInTheDocument();
  });

  it("shows a banner when the backend is unreachable", async () => {
    vi.spyOn(client, "getStatus").mockRejectedValue(new Error("network error"));
    vi.spyOn(client, "listBooks").mockResolvedValue({ books: [] });
    vi.spyOn(client, "getProgress").mockRejectedValue(new Error("network error"));

    render(<HomeView />);

    expect(await screen.findByText(/服务未响应/)).toBeInTheDocument();
  });
});
