import { useCallback, useEffect, useState } from "react";
import { deleteBook, listBooks, renameBook } from "../api/client";

export function useBooks() {
  const [books, setBooks] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const result = await listBooks();
      setBooks(result.books);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const remove = useCallback(
    async (bookId: string) => {
      try {
        await deleteBook(bookId);
        await refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    [refresh],
  );

  const rename = useCallback(
    async (bookId: string, newBookId: string) => {
      try {
        await renameBook(bookId, newBookId);
        await refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        throw e;
      }
    },
    [refresh],
  );

  return { books, error, refresh, remove, rename };
}
