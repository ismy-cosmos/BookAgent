import { useEffect } from "react";
import type { ImportProgress, LastResult } from "../api/types";
import { pausedRemainingText } from "../importProgressText";
import { Toast } from "@/components/shared/Toast";

const AUTO_DISMISS_MS = 6000;

interface ImportCompletionToastProps {
  result: LastResult;
  pausedAtProgress?: ImportProgress | null;
  onDismiss: () => void;
}

export function ImportCompletionToast({ result, pausedAtProgress, onDismiss }: ImportCompletionToastProps) {
  // 暂停打断跟真失败/真成功都不一样——用户主动叫它停的，不该定时消失，
  // 要让用户自己确认看到了再关掉。
  const autoDismiss = !result.aborted_early;

  useEffect(() => {
    if (!autoDismiss) return;
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [onDismiss, autoDismiss]);

  return (
    <Toast
      position="top-center"
      variant={result.error ? "error" : "neutral"}
      onDismiss={onDismiss}
    >
      {result.error ? (
        <span>导入失败：{result.error}</span>
      ) : result.aborted_early ? (
        <span>已暂停{pausedRemainingText(pausedAtProgress ?? null)}</span>
      ) : (
        <>
          <span>
            导入完成：入库 {result.total_chunks} 块
            {(result.failures?.length ?? 0) > 0 &&
              `，${result.failures!.length} 个文件失败`}
            {(result.not_attempted?.length ?? 0) > 0 &&
              `，${result.not_attempted!.length} 个文件未处理`}
          </span>
          {(result.failures?.length ?? 0) > 0 && (
            <details>
              <summary>查看失败详情</summary>
              <ul>
                {result.failures!.map((f) => (
                  <li key={f.file}>
                    {f.file}：{f.error_message}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </Toast>
  );
}
