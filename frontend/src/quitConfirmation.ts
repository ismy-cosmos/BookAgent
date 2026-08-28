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
 * 主窗口（HomeView）和每本书的对话窗口（ChatView）都会调用：关闭前先拦下
 * 关闭动作，交给调用方用应用内 Modal 弹确认框——原生 @tauri-apps/plugin-dialog
 * 的 confirm() 在 Linux 上（rfd 的 GTK3 后端）会把 title 同时塞进对话框正文
 * 加粗大标题和窗口标题栏两个位置，导致"确认退出"这行字重复出现两遍，且 API
 * 不给参数关掉其中一份——用应用内弹窗换掉，样式和交互跟删除确认统一，也不会
 * 有这个原生对话框的重复文字问题。
 * shouldConfirm 传函数而非快照值，保证监听器触发时读到的是当时最新的状态
 * （主窗口关心全局忙碌状态，对话窗口关心的是本窗口自己有没有问题在等，两种
 * 调用方各自决定要问的是什么，这里只负责统一的拦截-判断-弹出流程）。
 */
export async function installQuitConfirmation(
  shouldConfirm: () => boolean,
  onConfirmNeeded: () => void,
): Promise<() => void> {
  const current = getCurrentWindow();
  return current.onCloseRequested((event) => {
    if (!shouldConfirm()) return;
    event.preventDefault();
    onConfirmNeeded();
  });
}
