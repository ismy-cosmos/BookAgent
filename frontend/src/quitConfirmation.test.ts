import { describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: vi.fn(),
  getAllWindows: vi.fn(),
}));

import { getAllWindows, getCurrentWindow } from "@tauri-apps/api/window";
import { destroyAllWindows, installQuitConfirmation, shouldConfirmQuit } from "./quitConfirmation";
import type { Status } from "./api/types";

describe("shouldConfirmQuit", () => {
  it("returns true when busy", () => {
    const status: Status = { busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false };
    expect(shouldConfirmQuit(status)).toBe(true);
  });

  it("returns false when idle", () => {
    const status: Status = { busy: false, reason: "idle", book_id: null, pause_requested: false };
    expect(shouldConfirmQuit(status)).toBe(false);
  });
});

describe("installQuitConfirmation", () => {
  it("prevents the default close and calls onConfirmNeeded when busy, without touching any dialog API", async () => {
    let closeHandler: (event: { preventDefault: () => void }) => void = () => {};
    vi.mocked(getCurrentWindow).mockReturnValue({
      onCloseRequested: vi.fn((handler) => {
        closeHandler = handler;
        return Promise.resolve(() => {});
      }),
    } as unknown as ReturnType<typeof getCurrentWindow>);
    const onConfirmNeeded = vi.fn();

    await installQuitConfirmation(
      () => ({ busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false }),
      onConfirmNeeded,
    );
    const preventDefault = vi.fn();
    closeHandler({ preventDefault });

    expect(preventDefault).toHaveBeenCalledOnce();
    expect(onConfirmNeeded).toHaveBeenCalledOnce();
  });

  it("does nothing when idle", async () => {
    let closeHandler: (event: { preventDefault: () => void }) => void = () => {};
    vi.mocked(getCurrentWindow).mockReturnValue({
      onCloseRequested: vi.fn((handler) => {
        closeHandler = handler;
        return Promise.resolve(() => {});
      }),
    } as unknown as ReturnType<typeof getCurrentWindow>);
    const onConfirmNeeded = vi.fn();

    await installQuitConfirmation(
      () => ({ busy: false, reason: "idle", book_id: null, pause_requested: false }),
      onConfirmNeeded,
    );
    const preventDefault = vi.fn();
    closeHandler({ preventDefault });

    expect(preventDefault).not.toHaveBeenCalled();
    expect(onConfirmNeeded).not.toHaveBeenCalled();
  });
});

describe("destroyAllWindows", () => {
  it("destroys every window returned by getAllWindows", async () => {
    const destroyA = vi.fn();
    const destroyB = vi.fn();
    vi.mocked(getAllWindows).mockResolvedValue(
      [{ destroy: destroyA }, { destroy: destroyB }] as never,
    );

    await destroyAllWindows();

    expect(destroyA).toHaveBeenCalledOnce();
    expect(destroyB).toHaveBeenCalledOnce();
  });
});
