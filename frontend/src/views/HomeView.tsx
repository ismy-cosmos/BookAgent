import { useEffect, useRef, useState } from "react";
import { useStatus } from "../hooks/useStatus";
import { useImportProgress } from "../hooks/useImportProgress";
import { BookGrid } from "../components/BookGrid";
import { GlobalImportCapsule } from "../components/GlobalImportCapsule";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Toast } from "../components/Toast";
import { pauseImport } from "../api/client";
import { destroyAllWindows, installQuitConfirmation } from "../quitConfirmation";
import type { Status } from "../api/types";

export function HomeView() {
  const { status, unreachable } = useStatus();
  const { progress } = useImportProgress();
  const statusRef = useRef<Status>(status);
  statusRef.current = status;
  const [confirmingQuit, setConfirmingQuit] = useState(false);

  useEffect(() => {
    // StrictMode 开发模式下 effect 会 mount→cleanup→再 mount 一遍：
    // installQuitConfirmation 是异步的，第一次 cleanup 跑的时候 promise
    // 可能还没 resolve，unlisten 还是 undefined，cleanup 变成空操作——
    // 等 promise 真正 resolve 时已经晚了，两次注册都留了下来，导致
    // onCloseRequested 被挂了两个监听器（每次关闭弹两个确认框）。用
    // cancelled 标记：如果 promise resolve 时 effect 已经被清理过，直接
    // 反注册这次的监听器，不存进 unlisten。
    let cancelled = false;
    let unlisten: (() => void) | undefined;
    installQuitConfirmation(() => statusRef.current, () => setConfirmingQuit(true)).then((fn) => {
      if (cancelled) {
        fn();
      } else {
        unlisten = fn;
      }
    });
    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, []);

  return (
    <div style={{ padding: "var(--space-5)" }}>
      {unreachable && <Toast position="top-center">服务响应中</Toast>}
      {!unreachable && <BookGrid />}
      <GlobalImportCapsule progress={progress} onPause={() => pauseImport().catch(() => {})} />
      {confirmingQuit && (
        <ConfirmDialog
          message="导入正在进行，确定要退出吗？"
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
