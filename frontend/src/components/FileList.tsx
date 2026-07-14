import { useEffect, useRef, useState } from "react";
import { useFiles } from "../hooks/useFiles";
import { ConfirmDialog } from "./ConfirmDialog";
import type { ProgressResponse } from "../api/types";
import styles from "../ImportFileList.module.css";

interface FileListProps {
  bookId: string;
  progress: ProgressResponse | null;
}

export function FileList({ bookId, progress }: FileListProps) {
  const { files, remove, refresh } = useFiles(bookId);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  // 导入完成时每个文件成功入库会让"已导入文件"多一条——之前这里完全没
  // 接 progress，只在 bookId 变化时拉一次，导入完成后要切书再切回来才能
  // 看到新文件。用法跟 ImportPanel.tsx 里"待导入"列表的刷新时机一致：
  // 盯 busy/current_file/last_result 的内容变化，不是只看 busy 的布尔值
  // ——导入耗时可能短于轮询间隔，busy 从未被前端观察到变 true 过的情况下
  // 只有 last_result 的内容会变。
  //
  // 挂载那一刻 useFiles 自己已经拉过一次了（它内部的 mount effect），这里
  // 跳过第一次运行，避免挂载瞬间重复打两次 listFiles。
  const lastResultKey = JSON.stringify(progress?.last_result);
  const isFirstRender = useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    refresh();
  }, [refresh, progress?.busy, progress?.progress?.current_file, lastResultKey]);

  if (files.length === 0) return <p>暂无已导入文件</p>;

  return (
    <div>
      <h3 className={styles.heading}>已归档文件</h3>
      <ul className={styles.list}>
        {files.map((sourceFile) => (
          <li key={sourceFile} className={styles.row}>
            <span className={styles.filename}>{sourceFile}</span>
            <button className={styles.removeAction} onClick={() => setPendingDelete(sourceFile)}>
              删除
            </button>
          </li>
        ))}
      </ul>
      {pendingDelete && (
        <ConfirmDialog
          message={`确定要删除 '${pendingDelete}' 吗？此操作不可恢复。`}
          onConfirm={() => {
            remove(pendingDelete);
            setPendingDelete(null);
          }}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  );
}
