import { useState } from "react";
import type { ProgressResponse } from "../api/types";
import { stageText } from "../importProgressText";
import styles from "../GlobalImportCapsule.module.css";

interface GlobalImportCapsuleProps {
  progress: ProgressResponse | null;
  onPause: () => void;
}

export function GlobalImportCapsule({ progress, onPause }: GlobalImportCapsuleProps) {
  const [expanded, setExpanded] = useState(false);

  if (!progress?.busy) return null;

  if (!expanded) {
    return (
      <div
        className={styles.collapsed}
        data-testid="import-capsule"
        onClick={() => setExpanded(true)}
      >
        ⟳
      </div>
    );
  }

  return (
    <div
      className={styles.expanded}
      data-testid="import-capsule"
      onClick={() => setExpanded(false)}
    >
      <strong>正在导入《{progress.book_id}》</strong>
      <div>{progress.progress ? stageText(progress.progress) : ""}</div>
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
