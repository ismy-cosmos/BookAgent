import { useCallback, useRef } from "react";
import { useStatus } from "../hooks/useStatus";
import { useImportProgress } from "../hooks/useImportProgress";
import { useCloseConfirmation } from "../hooks/useCloseConfirmation";
import { BookGrid } from "@/components/book/BookGrid";
import { GlobalImportCapsule } from "../components/GlobalImportCapsule";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Toast } from "@/components/shared/Toast";
import { pauseImport } from "../api/client";
import { destroyAllWindows, shouldConfirmQuit } from "../quitConfirmation";
import type { Status } from "../api/types";

export function HomeView() {
  const { status, unreachable } = useStatus();
  const { progress } = useImportProgress();
  const statusRef = useRef<Status>(status);
  statusRef.current = status;
  const shouldConfirm = useCallback(() => shouldConfirmQuit(statusRef.current), []);
  const [confirmingQuit, setConfirmingQuit] = useCloseConfirmation(shouldConfirm);

  return (
    <div style={{ padding: "var(--space-5)" }}>
      {unreachable && <Toast position="top-center">服务响应中</Toast>}
      {!unreachable && <BookGrid />}
      <GlobalImportCapsule progress={progress} onPause={() => pauseImport().catch(() => {})} />
      {confirmingQuit && (
        <ConfirmDialog
          message={
            status.reason === "answering"
              ? "有对话正在处理中，确定要退出吗？"
              : "导入正在进行，确定要退出吗？"
          }
          confirmLabel="确定退出"
          onConfirm={() => {
            setConfirmingQuit(false);
            destroyAllWindows();
          }}
          onCancel={() => setConfirmingQuit(false)}
        />
      )}
    </div>
  );
}
