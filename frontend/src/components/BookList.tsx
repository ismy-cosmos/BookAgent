import { useState } from "react";
import { useBooks } from "../hooks/useBooks";
import type { Status } from "../api/types";
import { ConfirmDialog } from "./ConfirmDialog";

interface BookListProps {
  status: Status;
  selectedBook: string | null;
  onSelectBook: (bookId: string) => void;
}

export function BookList({ status, selectedBook, onSelectBook }: BookListProps) {
  const { books, remove } = useBooks();
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  return (
    <div>
      <ul>
        {books.map((bookId) => {
          const isImporting = status.busy && status.book_id === bookId;
          return (
            <li key={bookId}>
              <button onClick={() => onSelectBook(bookId)} aria-current={bookId === selectedBook}>
                {bookId}
              </button>
              <button
                disabled={isImporting}
                title={isImporting ? "导入中，暂不可删除" : undefined}
                onClick={() => setPendingDelete(bookId)}
              >
                删除
              </button>
            </li>
          );
        })}
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
