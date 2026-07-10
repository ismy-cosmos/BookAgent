import { describe, expect, it } from "vitest";
import { shouldConfirmQuit } from "./quitConfirmation";
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
