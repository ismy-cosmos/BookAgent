import { useEffect, useState } from "react";
import { installQuitConfirmation } from "@/quitConfirmation";

// HomeView（退出整个应用）和 ChatView（关闭这一个聊天窗口）都要装一个
// "关闭前先问一下"的监听器，判断标准不一样（前者看全局忙碌，后者只看
// 这本书自己），但注册/反注册这套流程完全相同，抽成一个共享 hook。
export function useCloseConfirmation(shouldConfirm: () => boolean) {
  const [confirming, setConfirming] = useState(false);

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
    installQuitConfirmation(shouldConfirm, () => setConfirming(true)).then((fn) => {
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
  }, [shouldConfirm]);

  return [confirming, setConfirming] as const;
}
