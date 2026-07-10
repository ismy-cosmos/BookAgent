import { useState } from "react";
import { useBooks } from "../hooks/useBooks";
import { useStatus } from "../hooks/useStatus";
import { BookCard } from "./BookCard";
import { openOrFocusWindow } from "../windowManager";

export function BookGrid() {
  const { books, remove, rename, refresh } = useBooks();
  const { status } = useStatus();
  const [creating, setCreating] = useState(false);
  const [newBookId, setNewBookId] = useState("");
  // 新建书不调用任何后端接口——书在首次导入成功前只存在于待导入列表，
  // 这里只是把它当"已存在"临时插进本地网格，直接带用户去导入窗口。
  const [pendingNewBooks, setPendingNewBooks] = useState<string[]>([]);

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const id = newBookId.trim();
    if (!id) return;
    setPendingNewBooks((prev) => (prev.includes(id) ? prev : [...prev, id]));
    openOrFocusWindow("import", id, id);
    setCreating(false);
    setNewBookId("");
  }

  const allBooks = [...books, ...pendingNewBooks.filter((id) => !books.includes(id))];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, 96px)", gap: 24, overflowY: "auto" }}>
      {allBooks.map((bookId) => (
        <BookCard
          key={bookId}
          bookId={bookId}
          busy={status.busy}
          importing={status.busy && status.book_id === bookId}
          onRemove={(id) => {
            remove(id);
            refresh();
          }}
          onRename={rename}
        />
      ))}
      {creating ? (
        <form onSubmit={handleCreate}>
          <input
            aria-label="新书 book_id"
            placeholder="输入 book_id"
            value={newBookId}
            onChange={(e) => setNewBookId(e.target.value)}
            autoFocus
          />
          <button type="submit">确定</button>
        </form>
      ) : (
        <button aria-label="新建书" onClick={() => setCreating(true)}>
          +
        </button>
      )}
    </div>
  );
}
