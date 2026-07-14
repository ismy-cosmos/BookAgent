import type { ImportProgress } from "./api/types";

// current_file/current_image 是后端在开始处理某一项*之前*就发出的
// 1-indexed"接下来处理第几个"指针，不是"已经完成几个"（跟
// GlobalImportCapsule.tsx 的 stagePercent() 是同一件事，那边已经有 -1
// 调整）——减 1 才是真正的完成度，否则唯一一个文件/图片刚开始处理就会
// 显示"1/1"，看起来像已经处理完了。
function positionText(p: ImportProgress): string {
  if (p.stage === "parsing" && p.current_file != null && p.total_files) {
    const name = p.current_filename ? ` · ${p.current_filename}` : "";
    return `${name}（${p.current_file - 1}/${p.total_files}）`;
  }
  if (p.stage === "vlm" && p.current_image != null && p.total_images) {
    return ` ${p.current_image - 1}/${p.total_images}`;
  }
  return "";
}

export function stageText(p: ImportProgress): string {
  if (p.stage === "parsing") return `解析中${positionText(p)}`;
  if (p.stage === "vlm") return `图片描述${positionText(p)}`;
  return "正在存储…";
}
