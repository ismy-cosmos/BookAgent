import { describe, expect, it, vi, beforeEach } from "vitest";

// vi.mock factories are hoisted above the whole file, so any variables they
// reference must be declared via vi.hoisted() — a plain top-level const
// declared below would still be undefined when the factory actually runs.
const { mockGetByLabel, mockSetFocus, mockDestroy, MockWebviewWindow } = vi.hoisted(() => {
  const mockGetByLabel = vi.fn();
  const mockSetFocus = vi.fn();
  const mockDestroy = vi.fn();
  const MockWebviewWindow = vi.fn();
  // vi.fn() returns a real function, so `new MockWebviewWindow(...)` works
  // and records the call in MockWebviewWindow.mock.calls; static getByLabel
  // just needs to be attached as an ordinary property.
  Object.assign(MockWebviewWindow, { getByLabel: mockGetByLabel });
  return { mockGetByLabel, mockSetFocus, mockDestroy, MockWebviewWindow };
});

vi.mock("@tauri-apps/api/webviewWindow", () => ({
  WebviewWindow: MockWebviewWindow,
}));

import { toWindowLabel, openOrFocusWindow, closeBookWindows, hasOpenWindows } from "./windowManager";

describe("toWindowLabel", () => {
  it("produces a label using only the Tauri-safe charset for arbitrary book_id content", () => {
    const label = toWindowLabel("chat", "民法典 2024 (draft)");
    expect(label).toMatch(/^chat-[A-Za-z0-9_-]+$/);
  });

  it("is deterministic for the same input", () => {
    expect(toWindowLabel("import", "ostep")).toBe(toWindowLabel("import", "ostep"));
  });

  it("produces different labels for different book_ids", () => {
    expect(toWindowLabel("chat", "book-a")).not.toBe(toWindowLabel("chat", "book-b"));
  });

  it("produces different labels for different kinds of the same book", () => {
    expect(toWindowLabel("chat", "ostep")).not.toBe(toWindowLabel("import", "ostep"));
  });
});

describe("openOrFocusWindow", () => {
  beforeEach(() => {
    mockGetByLabel.mockReset();
    mockSetFocus.mockReset();
    MockWebviewWindow.mockReset();
  });

  it("focuses an existing window instead of creating a new one", async () => {
    mockGetByLabel.mockResolvedValue({ setFocus: mockSetFocus });

    await openOrFocusWindow("chat", "ostep", "OSTEP");

    expect(mockSetFocus).toHaveBeenCalledOnce();
    expect(MockWebviewWindow).not.toHaveBeenCalled();
  });

  it("creates a new window when none exists for that label", async () => {
    mockGetByLabel.mockResolvedValue(null);

    await openOrFocusWindow("import", "ostep", "OSTEP");

    expect(MockWebviewWindow).toHaveBeenCalledOnce();
    const [label, options] = MockWebviewWindow.mock.calls[0];
    expect(label).toBe(toWindowLabel("import", "ostep"));
    expect(options.title).toBe("OSTEP");
    expect(options.url).toContain("view=import");
    expect(options.url).toContain(`book=${encodeURIComponent("ostep")}`);
  });
});

describe("closeBookWindows", () => {
  beforeEach(() => {
    mockGetByLabel.mockReset();
    mockDestroy.mockReset();
  });

  it("destroys both the import and chat windows for a book when they're open", async () => {
    mockGetByLabel.mockResolvedValue({ destroy: mockDestroy });

    await closeBookWindows("ostep");

    expect(mockGetByLabel).toHaveBeenCalledWith(toWindowLabel("import", "ostep"));
    expect(mockGetByLabel).toHaveBeenCalledWith(toWindowLabel("chat", "ostep"));
    expect(mockDestroy).toHaveBeenCalledTimes(2);
  });

  it("does nothing when neither window is open", async () => {
    mockGetByLabel.mockResolvedValue(null);

    await closeBookWindows("ostep");

    expect(mockDestroy).not.toHaveBeenCalled();
  });
});

describe("hasOpenWindows", () => {
  beforeEach(() => {
    mockGetByLabel.mockReset();
  });

  it("returns true when the import window is open", async () => {
    mockGetByLabel.mockImplementation(async (label: string) =>
      label === toWindowLabel("import", "ostep") ? { setFocus: mockSetFocus } : null,
    );

    expect(await hasOpenWindows("ostep")).toBe(true);
  });

  it("returns true when the chat window is open", async () => {
    mockGetByLabel.mockImplementation(async (label: string) =>
      label === toWindowLabel("chat", "ostep") ? { setFocus: mockSetFocus } : null,
    );

    expect(await hasOpenWindows("ostep")).toBe(true);
  });

  it("returns false when neither window is open", async () => {
    mockGetByLabel.mockResolvedValue(null);

    expect(await hasOpenWindows("ostep")).toBe(false);
  });
});
