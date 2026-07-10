import { useEffect, useRef } from "react";
import { useStatus } from "../hooks/useStatus";
import { useImportProgress } from "../hooks/useImportProgress";
import { BookGrid } from "../components/BookGrid";
import { GlobalImportCapsule } from "../components/GlobalImportCapsule";
import { pauseImport } from "../api/client";
import { installQuitConfirmation } from "../quitConfirmation";
import type { Status } from "../api/types";

export function HomeView() {
  const { status, unreachable } = useStatus();
  const { progress } = useImportProgress();
  const statusRef = useRef<Status>(status);
  statusRef.current = status;

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    installQuitConfirmation(() => statusRef.current).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, []);

  return (
    <div>
      <h1>BookAgent</h1>
      {unreachable && <div role="alert">服务未响应，重试中…</div>}
      {!unreachable && <BookGrid />}
      <GlobalImportCapsule progress={progress} onPause={() => pauseImport().catch(() => {})} />
    </div>
  );
}
