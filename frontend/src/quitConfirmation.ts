import { getAllWindows, getCurrentWindow } from "@tauri-apps/api/window";
import { confirm } from "@tauri-apps/plugin-dialog";
import type { Status } from "./api/types";

export function shouldConfirmQuit(status: Status): boolean {
  return status.busy;
}

/**
 * 只在主窗口调用：导入中关闭主窗口先弹确认框，确认后把所有窗口一起销毁
 * （销毁而非再次 close，避免重新触发 close-requested 造成死循环）。
 * getStatus 传函数而非快照值，保证监听器触发时读到的是当时最新的忙碌状态。
 */
export async function installQuitConfirmation(
  getStatus: () => Status,
): Promise<() => void> {
  const current = getCurrentWindow();
  return current.onCloseRequested(async (event) => {
    if (!shouldConfirmQuit(getStatus())) return;
    event.preventDefault();
    const confirmed = await confirm("导入正在进行，确定要退出吗？", {
      title: "确认退出",
      kind: "warning",
    });
    if (confirmed) {
      for (const w of await getAllWindows()) {
        await w.destroy();
      }
    }
  });
}
