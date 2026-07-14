import { describe, expect, it } from "vitest";
import { stageText } from "./importProgressText";

describe("stageText", () => {
  // current_file/current_image 是后端在开始处理某一项*之前*就发出的
  // 1-indexed"接下来处理第几个"指针，不是"已经完成几个"（跟
  // GlobalImportCapsule.tsx 的 stagePercent() 是同一件事，那边已经有
  // -1 调整）——显示时要减 1 才是真正的完成度，否则唯一一个文件/图片
  // 刚开始处理就会显示"1/1"，看起来像已经处理完了。

  it("解析阶段：文件名+位置（已完成数 = current_file - 1）", () => {
    expect(stageText({
      stage: "parsing", current_file: 2, total_files: 3,
      current_image: null, total_images: null, current_filename: "ch02.pdf",
    })).toBe("解析中 · ch02.pdf（1/3）");
  });

  it("解析阶段：唯一一个文件刚开始处理时显示 0/1，不是 1/1", () => {
    expect(stageText({
      stage: "parsing", current_file: 1, total_files: 1,
      current_image: null, total_images: null,
    })).toBe("解析中（0/1）");
  });

  it("图片描述阶段：只显示聚合位置，不带文件名", () => {
    expect(stageText({
      stage: "vlm", current_file: null, total_files: null,
      current_image: 7, total_images: 40, current_filename: null,
    })).toBe("图片描述 6/40");
  });

  it("存储阶段：静态文案，没有位置信息", () => {
    expect(stageText({
      stage: "storing", current_file: null, total_files: null,
      current_image: null, total_images: null,
    })).toBe("正在存储…");
  });
});
