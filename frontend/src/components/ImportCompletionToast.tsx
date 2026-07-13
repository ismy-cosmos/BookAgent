import { useEffect } from "react";
import type { LastResult } from "../api/types";
import { Toast } from "./Toast";

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
    <Toast position="top-center" onDismiss={onDismiss}>
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
    </Toast>
  );
}
