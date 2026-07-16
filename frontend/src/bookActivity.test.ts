import { describe, expect, it } from "vitest";
import { bookActivity } from "./bookActivity";
import type { Status } from "./api/types";

function status(overrides: Partial<Status>): Status {
  return { busy: false, reason: "idle", book_id: null, pause_requested: false, ...overrides };
}

describe("bookActivity", () => {
  it("returns idle when status is null", () => {
    expect(bookActivity(null, "ostep")).toBe("idle");
  });

  it("returns idle when nothing is busy", () => {
    expect(bookActivity(status({}), "ostep")).toBe("idle");
  });

  it("returns idle when a different book is busy", () => {
    const s = status({ busy: true, reason: "ingesting", book_id: "other-book" });
    expect(bookActivity(s, "ostep")).toBe("idle");
  });

  it("returns ingesting when this book is being imported", () => {
    const s = status({ busy: true, reason: "ingesting", book_id: "ostep" });
    expect(bookActivity(s, "ostep")).toBe("ingesting");
  });

  it("returns answering when this book is being asked a question", () => {
    const s = status({ busy: true, reason: "answering", book_id: "ostep" });
    expect(bookActivity(s, "ostep")).toBe("answering");
  });
});
