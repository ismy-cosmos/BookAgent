import { useState } from "react";
import { BookList } from "../components/BookList";
import { useStatus } from "../hooks/useStatus";
import { useImportProgress } from "../hooks/useImportProgress";
import { openOrFocusWindow } from "../windowManager";

export function HomeView() {
  const { status, unreachable } = useStatus();
  useImportProgress();
  const [selectedBook, setSelectedBook] = useState<string | null>(null);

  return (
    <div>
      <h1>BookAgent</h1>
      {unreachable && <div role="alert">服务未响应，重试中…</div>}
      {!unreachable && (
        <BookList
          status={status}
          selectedBook={selectedBook}
          onSelectBook={(bookId) => {
            setSelectedBook(bookId);
            openOrFocusWindow("import", bookId, bookId);
          }}
        />
      )}
    </div>
  );
}
