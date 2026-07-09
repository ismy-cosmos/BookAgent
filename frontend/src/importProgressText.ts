import type { ImportProgress } from "./api/types";

export function stageText(p: ImportProgress): string {
  if (p.stage === "parsing") return `解析中 文件 ${p.current_file}/${p.total_files}`;
  if (p.stage === "vlm") return `图片描述 ${p.current_image}/${p.total_images}`;
  return "正在存储…";
}
