import { useEffect, useState } from "react";
import { getProgress } from "@/api/client";
import type { ProgressResponse } from "@/api/types";

// GET /progress 只是读内存字典（ImportQueue.get_progress()，加锁复制无 I/O），
// 前后端都在本机 127.0.0.1，缩短轮询间隔不会有实质性能影响。500ms 是为了让
// 缓存命中导致的"极快导入"（整个任务可能几百毫秒内跑完）也能被轮询捕捉到，
// 不至于进度文案卡在最后一次瞬间快照上。
const POLL_INTERVAL_MS = 500;

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
