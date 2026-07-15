import { useState } from "react";
import type { ImportProgress, ProgressResponse } from "../api/types";
import { stageText } from "../importProgressText";
import styles from "../GlobalImportCapsule.module.css";

interface GlobalImportCapsuleProps {
  progress: ProgressResponse | null;
  onPause: () => void;
}

const STAGES = ["parsing", "vlm", "storing"] as const;
const STAGE_LABEL: Record<(typeof STAGES)[number], string> = {
  parsing: "解析",
  vlm: "图片",
  storing: "存储",
};

// 三个阶段各自独立算完成度，互不混算成一个总百分比——阶段耗时差异很大
// （存储通常很快，图片描述可能很慢），硬凑权重只会制造新的"卡在 90% 很久"
// 式误导。阶段3（存储）没有任何可计算的进度信号（Plan 1 复核代码时确认——
// ProgressUpdate 在 storing 阶段只发一条静态事件，不带 current/total），
// 不假装知道百分比，用动画条表示"在跑但不知道还要多久"。
//
// current_file/current_image 是后端在处理某个文件/图片*开始前*就发出的
// 1-indexed"当前在第几个"指针（scripts/ingest.py 解析循环里 on_progress
// 在 _parse_file 之前调用，current_file=idx+1），不是"已完成计数"。总数为
// 1 时不减这个 1，正在解析唯一那个文件就会直接显示"1/1，100%"，看起来
// 已经做完了、其实还在跑——所以这里要减 1 才是真正的完成度。
function stagePercent(stage: (typeof STAGES)[number], p: ImportProgress): number {
  if (stage === "parsing" && p.stage === "parsing" && p.current_file != null && p.total_files) {
    return Math.round(((p.current_file - 1) / p.total_files) * 100);
  }
  if (stage === "vlm" && p.stage === "vlm" && p.current_image != null && p.total_images) {
    return Math.round(((p.current_image - 1) / p.total_images) * 100);
  }
  // storing 是最后一个阶段，不可能有"已经跑过 storing"这回事——真到了
  // storing 阶段，渲染那边走的是 indeterminate 动画，根本不会调用这里；
  // 走到这一行的 storing 恒为"还没轮到"，固定 0%。
  if (stage === "storing") return 0;
  // 还没轮到这个阶段：0%；已经跑过这个阶段（当前阶段在它后面）：100%
  return STAGES.indexOf(p.stage) > STAGES.indexOf(stage) ? 100 : 0;
}

export function GlobalImportCapsule({ progress, onPause }: GlobalImportCapsuleProps) {
  const [expanded, setExpanded] = useState(false);

  if (!progress?.busy || progress.reason !== "ingesting") return null;
  const p = progress.progress;

  if (!expanded) {
    const label = p
      ? p.stage === "storing"
        ? "存储中"
        : `${STAGE_LABEL[p.stage]} ${stagePercent(p.stage, p)}%`
      : "";
    return (
      <div
        className={styles.collapsed}
        data-testid="import-capsule"
        onClick={() => setExpanded(true)}
      >
        <span className={styles.spinner} />
        <span>{label}</span>
      </div>
    );
  }

  return (
    <div
      className={styles.expanded}
      data-testid="import-capsule"
      onClick={() => setExpanded(false)}
    >
      <div className={styles.header}>
        <strong>正在导入《{progress.book_id}》</strong>
      </div>
      <div className={styles.stageText}>{p ? stageText(p) : ""}</div>
      <div className={styles.progressTrack}>
        {STAGES.map((stage) => {
          const isStoringIndeterminate = stage === "storing" && p?.stage === "storing";
          return (
            <div key={stage} className={styles.progressSegment}>
              <div
                data-testid={`progress-segment-${stage}`}
                className={
                  isStoringIndeterminate
                    ? `${styles.progressSegmentFill} ${styles.indeterminate}`
                    : styles.progressSegmentFill
                }
                style={
                  isStoringIndeterminate
                    ? undefined
                    : { width: `${p ? stagePercent(stage, p) : 0}%` }
                }
              />
            </div>
          );
        })}
      </div>
      <button
        className={styles.pauseButton}
        onClick={(e) => {
          e.stopPropagation();
          onPause();
        }}
      >
        暂停
      </button>
    </div>
  );
}
