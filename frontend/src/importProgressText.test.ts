import { describe, expect, it } from "vitest";
import { stageText } from "./importProgressText";

describe("stageText", () => {
  it("解析阶段：文件名+位置", () => {
    expect(stageText({
      stage: "parsing", current_file: 2, total_files: 3,
      current_image: null, total_images: null, current_filename: "ch02.pdf",
    })).toBe("解析中 · ch02.pdf（2/3）");
  });

  it("解析阶段：current_filename 缺失时不显示文件名部分", () => {
    expect(stageText({
      stage: "parsing", current_file: 1, total_files: 1,
      current_image: null, total_images: null,
    })).toBe("解析中（1/1）");
  });

  it("图片描述阶段：只显示聚合位置，不带文件名", () => {
    expect(stageText({
      stage: "vlm", current_file: null, total_files: null,
      current_image: 7, total_images: 40, current_filename: null,
    })).toBe("图片描述 7/40");
  });

  it("存储阶段：静态文案，没有位置信息", () => {
    expect(stageText({
      stage: "storing", current_file: null, total_files: null,
      current_image: null, total_images: null,
    })).toBe("正在存储…");
  });
});
