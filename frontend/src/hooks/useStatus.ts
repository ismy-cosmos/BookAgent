import { useEffect, useState } from "react";
import { getStatus } from "../api/client";
import type { Status } from "../api/types";

const POLL_INTERVAL_MS = 2000;

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
