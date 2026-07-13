import { useCallback, useEffect, useState } from "react";
import { deleteBook, listBooks, renameBook } from "../api/client";
import { toErrorMessage } from "../errorMessage";

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
