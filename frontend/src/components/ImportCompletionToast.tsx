import { useEffect } from "react";
import type { LastResult } from "../api/types";

const AUTO_DISMISS_MS = 6000;

interface ImportCompletionToastProps {
  result: LastResult;
  onDismiss: () => void;
}

export function ImportCompletionToast({ result, onDismiss }: ImportCompletionToastProps) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      role="status"
      style={{
        position: "fixed",
        top: "1rem",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 1000,
      }}
    >
      <button aria-label="关闭" onClick={onDismiss}>×</button>
      {result.error ? (
        <span>导入失败：{result.error}</span>
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
    </div>
  );
}
