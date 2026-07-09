import { useState } from "react";
import { useFiles } from "../hooks/useFiles";
import { ConfirmDialog } from "./ConfirmDialog";

interface FileListProps {
  bookId: string;
}

export function FileList({ bookId }: FileListProps) {
  const { files, remove } = useFiles(bookId);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  if (files.length === 0) return <p>暂无已导入文件</p>;

  return (
    <div>
      <h3>已导入文件</h3>
      <ul>
        {files.map((sourceFile) => (
          <li key={sourceFile}>
            {sourceFile}
            <button onClick={() => setPendingDelete(sourceFile)}>删除</button>
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
