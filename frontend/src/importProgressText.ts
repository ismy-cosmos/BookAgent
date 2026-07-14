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
