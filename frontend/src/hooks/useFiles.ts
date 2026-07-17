import { useCallback, useEffect, useState } from "react";
import { ApiError, deleteFile, listFiles } from "@/api/client";
import { toErrorMessage } from "@/errorMessage";

export function useFiles(bookId: string) {
  const [files, setFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const result = await listFiles(bookId);
      setFiles(result.files);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        // 新建的书在首次导入成功前 Chroma collection 不存在——不算错误，按空列表处理
        setFiles([]);
      } else {
        setError(toErrorMessage(e));
      }
    }
  }, [bookId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const remove = useCallback(
    async (sourceFile: string) => {
      try {
        await deleteFile(bookId, sourceFile);
        await refresh();
      } catch (e) {
        setError(toErrorMessage(e));
      }
    },
    [bookId, refresh],
  );

  return { files, error, refresh, remove };
}
