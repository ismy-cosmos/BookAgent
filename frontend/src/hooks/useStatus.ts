import { useEffect, useState } from "react";
import { getStatus } from "@/api/client";
import type { Status } from "@/api/types";

// 跟 useImportProgress.ts 的轮询间隔保持一致——/progress 的响应本来就是
// /status 的超集（ProgressResponse extends Status），没有理由这两个轮询
// 跑不同的节奏。500ms 这个频率已经在 useImportProgress 那边验证过没问题
// （本地 loopback 请求，桌面单用户场景）。
const POLL_INTERVAL_MS = 500;

const IDLE_STATUS: Status = { busy: false, reason: "idle", book_id: null, pause_requested: false };

export function useStatus() {
  const [status, setStatus] = useState<Status>(IDLE_STATUS);
  const [unreachable, setUnreachable] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const result = await getStatus();
        if (!cancelled) {
          setStatus(result);
          setUnreachable(false);
        }
      } catch {
        if (!cancelled) setUnreachable(true);
      }
    }

    poll();
    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return { status, unreachable };
}
