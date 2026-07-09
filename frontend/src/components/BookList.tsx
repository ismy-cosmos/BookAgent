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
  const [creating, setCreating] = useState(false);
  const [newBookId, setNewBookId] = useState("");

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const id = newBookId.trim();
    if (!id) return;
    // 书在首次导入成功前只存在于待导入列表——这里不调任何后端接口，
    // 直接"选中"这个新 id，用户在它的书页里加文件、点开始导入
    onSelectBook(id);
    setCreating(false);
    setNewBookId("");
  }

  return (
    <div>
      <button onClick={() => setCreating(true)}>新建书</button>
      {creating && (
        <form onSubmit={handleCreate}>
          <input
            aria-label="新书 book_id"
            placeholder="输入 book_id"
            value={newBookId}
            onChange={(e) => setNewBookId(e.target.value)}
          />
          <button type="submit">确定</button>
        </form>
      )}
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
