import { useCallback, useEffect, useState } from "react";
import { addStagedFile, listStagedFiles, removeStagedFile } from "../api/client";
import { toErrorMessage } from "../errorMessage";

export function useStagedFiles(bookId: string) {
  const [files, setFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const result = await listStagedFiles(bookId);
      setFiles(result.files);
    } catch (e) {
      setError(toErrorMessage(e));
    }
  }, [bookId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const add = useCallback(
    async (paths: string[]) => {
      try {
        // 后端是单文件接口，逐个提交；每次响应都是完整列表，取最后一次即可
        let latest: string[] | null = null;
        for (const path of paths) {
          latest = (await addStagedFile(bookId, path)).files;
        }
        if (latest) setFiles(latest);
      } catch (e) {
        setError(toErrorMessage(e));
      }
    },
    [bookId],
  );

  const remove = useCallback(
    async (path: string) => {
      try {
        const result = await removeStagedFile(bookId, path);
        setFiles(result.files);
      } catch (e) {
        setError(toErrorMessage(e));
      }
    },
    [bookId],
  );

  return { files, error, refresh, add, remove, setError };
}
