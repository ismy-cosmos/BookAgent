import { getAllWindows, getCurrentWindow } from "@tauri-apps/api/window";
import type { Status } from "./api/types";

export function shouldConfirmQuit(status: Status): boolean {
  return status.busy;
}

// 销毁而非再次 close，避免重新触发 close-requested 造成死循环。
export async function destroyAllWindows(): Promise<void> {
  for (const w of await getAllWindows()) {
    await w.destroy();
  }
}

/**
 * 只在主窗口调用：导入中关闭主窗口先拦下关闭动作，交给调用方（HomeView）
 * 用应用内 Modal 弹确认框——原生 @tauri-apps/plugin-dialog 的 confirm() 在
 * Linux 上（rfd 的 GTK3 后端）会把 title 同时塞进对话框正文加粗大标题和
 * 窗口标题栏两个位置，导致"确认退出"这行字重复出现两遍，且 API 不给参数
 * 关掉其中一份——用应用内弹窗换掉，样式和交互跟删除确认统一，也不会有
 * 这个原生对话框的重复文字问题。
 * getStatus 传函数而非快照值，保证监听器触发时读到的是当时最新的忙碌状态。
 */
export async function installQuitConfirmation(
  getStatus: () => Status,
  onConfirmNeeded: () => void,
): Promise<() => void> {
  const current = getCurrentWindow();
  return current.onCloseRequested((event) => {
    if (!shouldConfirmQuit(getStatus())) return;
    event.preventDefault();
    onConfirmNeeded();
  });
}
