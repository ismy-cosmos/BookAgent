import { describe, expect, it } from "vitest";
import { citationLabel } from "./citationLabel";
import type { Citation } from "./api/types";

const citation: Citation = {
  chunk_id: "c1", source_file: "f.pdf", element_type: "text",
  citation: "f.pdf p.1", score: 0.9,
};

describe("citationLabel", () => {
  it("有引用时返回 pills，不管 attemptedRetrieve 是什么", () => {
    expect(citationLabel([citation], false)).toEqual({ kind: "pills", citations: [citation] });
    expect(citationLabel([citation], true)).toEqual({ kind: "pills", citations: [citation] });
  });

  it("无引用且确实检索过：书中未检索到相关内容", () => {
    expect(citationLabel([], true)).toEqual({ kind: "text", text: "书中未检索到相关内容" });
  });

  it("无引用且没有重新检索：本轮未重新检索原文", () => {
    expect(citationLabel([], false)).toEqual({ kind: "text", text: "本轮未重新检索原文" });
  });
});
