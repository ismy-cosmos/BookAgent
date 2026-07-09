import { useCallback, useEffect, useState } from "react";
import { deleteBook, listBooks } from "../api/client";

export function useBooks() {
  const [books, setBooks] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const result = await listBooks();
      setBooks(result.books);
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

  return { books, error, refresh, remove };
}
