import { useEffect, useState } from "react";
import { getProgress } from "../api/client";
import type { ProgressResponse } from "../api/types";

const POLL_INTERVAL_MS = 2000;

export function useImportProgress() {
  const [progress, setProgress] = useState<ProgressResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const result = await getProgress();
        if (!cancelled) setProgress(result);
      } catch {
        // 轮询失败保持上一次的值——"后端不可达"的用户提示由 useStatus.unreachable 负责
      }
    }

    poll();
    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return { progress };
}
