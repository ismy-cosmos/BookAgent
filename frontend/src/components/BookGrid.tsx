import { useState } from "react";
import { useBooks } from "../hooks/useBooks";
import { useStatus } from "../hooks/useStatus";
import { BookCard } from "./BookCard";
import { NewBookDialog } from "./NewBookDialog";
import { openOrFocusWindow } from "../windowManager";
import styles from "../BookGrid.module.css";

export function BookGrid() {
  const { books, remove, rename, refresh } = useBooks();
  const { status } = useStatus();
  const [creating, setCreating] = useState(false);
  // 新建书不调用任何后端接口——书在首次导入成功前只存在于待导入列表，
  // 这里只是把它当"已存在"临时插进本地网格，直接带用户去导入窗口。
  const [pendingNewBooks, setPendingNewBooks] = useState<string[]>([]);

  function handleCreate(id: string) {
    setPendingNewBooks((prev) => (prev.includes(id) ? prev : [...prev, id]));
    openOrFocusWindow("import", id, id);
    setCreating(false);
  }

  // 待导入的书只存在于本地 pendingNewBooks，后端从没建过它，删除时不能走
  // 后端接口（会 404 且什么都不会发生），直接从本地列表摘掉即可。
  function handleRemove(id: string) {
    if (pendingNewBooks.includes(id)) {
      setPendingNewBooks((prev) => prev.filter((b) => b !== id));
      return;
    }
    remove(id);
    refresh();
  }

  const allBooks = [...books, ...pendingNewBooks.filter((id) => !books.includes(id))];

  return (
    <div className={styles.grid}>
      {allBooks.map((bookId) => (
        <BookCard
          key={bookId}
          bookId={bookId}
          busy={status.busy}
          importing={status.busy && status.book_id === bookId}
          onRemove={handleRemove}
          onRename={rename}
        />
      ))}
      <button className={styles.addTile} aria-label="新建书" onClick={() => setCreating(true)}>
        +
      </button>
      {creating && (
        <NewBookDialog onCreate={handleCreate} onCancel={() => setCreating(false)} />
      )}
    </div>
  );
}
