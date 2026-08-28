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

// "已暂停"弹窗要报还剩多少没处理——用暂停生效前最后一次真实轮询到的
// 快照算，不是 not_attempted 的文件数：not_attempted 在阶段2中断时存的
// 是"文件"，但暂停实际打断的是"图片"，拿文件数冒充图片数会不准。
// 返回值前面带逗号，直接拼在"已暂停"后面用（"已暂停" + 这个函数的返回值）。
export function pausedRemainingText(p: ImportProgress | null): string {
  if (p?.stage === "parsing" && p.current_file != null && p.total_files) {
    const remaining = p.total_files - (p.current_file - 1);
    // current_file 永远不会超过 total_files，所以"正在处理最后一个文件"
    // 这份快照算出来的剩余数只会是 1，不可能是 0——这个 1 不是真的
    // "还有1个文件没解析"，是"最后一个文件正在处理、还没确认完成"。这个
    // 文件实际上会正常处理完，阶段1 完整结束，真正被打断的是阶段2（图片
    // 描述）。阶段2 那次中断可能快到没有任何真实耗时（一张图片的 VLM
    // 请求都没发出去就直接跳出了），轮询很可能根本没捕捉到那一瞬间的
    // 快照，这份记录还停留在这个"最后一个文件"的旧值上——继续按阶段1
    // 的口径硬报数字文不对题，退化成不带数字的图片待处理。
    if (remaining <= 1) return "，图片待处理";
    return `，还有 ${remaining} 个文件未解析`;
  }
  if (p?.stage === "vlm" && p.current_image != null && p.total_images) {
    // 阶段2→阶段3 不需要同款兜底：阶段2 处理到最后一张图片时暂停，会
    // 直接让阶段3（入库，无暂停检查点、很快）正常跑完，这种情况下
    // aborted_early 本来就是 false，走的是普通"导入完成"，不会用到
    // 这份"已暂停"文案。
    return `，还有 ${p.total_images - (p.current_image - 1)} 张图片未处理`;
  }
  // 存储阶段（阶段3）没有位置数据可用（只发一条静态标记），也没有暂停
  // 检查点——如果最后停在这个阶段，说明是别的原因中止的（比如连续失败），
  // 不编数字。progress 为 null（完全没捕捉到任何快照）时也走这条兜底。
  return "，还有文件未入库";
}
