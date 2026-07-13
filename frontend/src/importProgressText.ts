import type { ImportProgress } from "./api/types";

function positionText(p: ImportProgress): string {
  if (p.stage === "parsing") {
    const name = p.current_filename ? ` · ${p.current_filename}` : "";
    return `${name}（${p.current_file}/${p.total_files}）`;
  }
  if (p.stage === "vlm") return ` ${p.current_image}/${p.total_images}`;
  return "";
}

export function stageText(p: ImportProgress): string {
  if (p.stage === "parsing") return `解析中${positionText(p)}`;
  if (p.stage === "vlm") return `图片描述${positionText(p)}`;
  return "正在存储…";
}

// 暂停只可能打断在 parsing/vlm 阶段（阶段3 存储没有暂停检查点，一旦开始
// 会跑到底），positionText 对这两个阶段总能算出有意义的位置文案。
export function pausedText(p: ImportProgress): string {
  return `已暂停${positionText(p)}`;
}
