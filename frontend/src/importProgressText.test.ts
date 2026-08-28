import { describe, expect, it } from "vitest";
import { pausedRemainingText, stageText } from "./importProgressText";

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

describe("pausedRemainingText", () => {
  it("最后停在解析阶段：显示还未解析的文件数（前面带逗号，拼在'已暂停'后面）", () => {
    expect(pausedRemainingText({
      stage: "parsing", current_file: 2, total_files: 5,
      current_image: null, total_images: null,
    })).toBe("，还有 4 个文件未解析");
  });

  it("最后停在图片描述阶段：显示还未处理的图片数（量词是张，不是个）", () => {
    expect(pausedRemainingText({
      stage: "vlm", current_file: null, total_files: null,
      current_image: 3, total_images: 10,
    })).toBe("，还有 8 张图片未处理");
  });

  it("解析阶段快照停在最后一个文件（剩余算出来是1）：真正被打断的是阶段2，不能报'还有1个文件未解析'", () => {
    // current_file 永远不会超过 total_files，所以"正在处理最后一个文件"
    // 这个快照算出来的剩余数只会是 1，永远不可能是 0——这个 1 不是真的
    // "还有1个文件没解析"，是"最后一个文件正在处理、还没确认完成"。
    // 这个文件实际上会正常处理完，阶段1 完整结束，真正被打断的是阶段2
    // （图片描述），阶段2 那次中断可能快到没有任何真实耗时（没发出任何
    // VLM 请求就直接跳出了），轮询很可能根本没捕捉到那一瞬间的快照，
    // 还停留在这份"最后一个文件"的旧快照上。这时候不能按阶段1 的口径
    // 硬报数字，退化成不带数字的图片待处理文案。
    expect(pausedRemainingText({
      stage: "parsing", current_file: 5, total_files: 5,
      current_image: null, total_images: null,
    })).toBe("，图片待处理");
  });

  it("最后停在存储阶段：这个阶段没有位置数据，不编数字", () => {
    // 阶段3 只发一条静态标记（ProgressUpdate(stage="storing")），不带
    // current_file/total_files——真实触发场景：阶段1/2 都正常跑完，
    // 阶段3 因为连续失败被中止（不是暂停打断，阶段3本来就没有暂停检查点）。
    expect(pausedRemainingText({
      stage: "storing", current_file: null, total_files: null,
      current_image: null, total_images: null,
    })).toBe("，还有文件未入库");
  });

  it("完全没有捕捉到任何快照时的兜底", () => {
    expect(pausedRemainingText(null)).toBe("，还有文件未入库");
  });
});
