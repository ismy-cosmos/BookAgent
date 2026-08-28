import { useCallback, useEffect, useState } from "react";
import { deleteBook, listBooks, renameBook } from "@/api/client";
import { toErrorMessage } from "@/errorMessage";
import { closeBookWindows, hasOpenWindows } from "@/windowManager";

export function useBooks() {
  const [books, setBooks] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const result = await listBooks();
      setBooks(result.books);
      setError(null);
    } catch (e) {
      setError(toErrorMessage(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const remove = useCallback(
    async (bookId: string) => {
      try {
        await deleteBook(bookId);
        // 书删掉之后，它对应的导入/对话窗口如果还开着，会一直留着删除
        // 前的内存状态——同名书重新建出来时，openOrFocusWindow 按 label
        // 找到的是这个没被销毁的旧窗口，直接聚焦、不会重新拉取数据。
        await closeBookWindows(bookId);
        await refresh();
      } catch (e) {
        setError(toErrorMessage(e));
      }
    },
    [refresh],
  );

  const rename = useCallback(
    async (bookId: string, newBookId: string) => {
      try {
        // 改名会改变 book_id，而窗口 label／窗口内部状态都认定 bookId
        // 不会变——与其改名后想办法把窗口迁移到新 label，不如改名前
        // 先查窗口开没开，开着就直接拒绝。
        if (await hasOpenWindows(bookId)) {
          throw new Error(`'${bookId}' 有窗口正在打开，请先关闭再改名`);
        }
        await renameBook(bookId, newBookId);
        await refresh();
      } catch (e) {
        setError(toErrorMessage(e));
        throw e;
      }
    },
    [refresh],
  );

  return { books, error, refresh, remove, rename, setError };
}
