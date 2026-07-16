import { useState } from "react";
import { bookActivity } from "../bookActivity";
import { useBooks } from "../hooks/useBooks";
import { useStatus } from "../hooks/useStatus";
import { BookCard } from "./BookCard";
import { NewBookDialog } from "./NewBookDialog";
import { Toast } from "./Toast";
import { closeBookWindows, openOrFocusWindow } from "../windowManager";
import { ApiError, deleteBook } from "../api/client";
import styles from "../BookGrid.module.css";

export function BookGrid() {
  const { books, error, setError, remove, rename } = useBooks();
  const { status } = useStatus();
  const [creating, setCreating] = useState(false);
  // 新建书不调用任何后端接口——GET /books 要等这本书的 collection 第一次
  // 被创建才查得到（阶段3 _store_file 循环第一步 store.get() 就会触发
  // get_or_create_collection，比真正写入第一个 chunk 还早一步），在那之前
  // 这里只是把它当"已存在"临时插进本地网格，直接带用户去导入窗口。
  const [pendingNewBooks, setPendingNewBooks] = useState<string[]>([]);

  function handleCreate(id: string) {
    setPendingNewBooks((prev) => (prev.includes(id) ? prev : [...prev, id]));
    openOrFocusWindow("import", id, id);
    setCreating(false);
  }

  // 待导入的书本地看起来"还没建过"，但用户很可能已经在导入窗口点过
  // "开始导入"——后端可能有一个真实任务正在跑/排队。不能只凭本地这份
  // pendingNewBooks 就断定后端什么都没有，必须真的打一次删除接口，让后端
  // 的忙碌检查（book_has_pending_or_active_task）说了算：
  // - 404：后端确认这本书从没建出真实 collection（真的没提交过，或提交过
  //   但一个 chunk 都没成功入库），本地这条记录可以放心摘掉。
  // - 409／其他错误：后端有真实状态要保护，必须原样告诉用户，绝不能把
  //   卡片摘掉——否则用户以为删除成功，实际上后台任务还在跑，等它跑完
  //   存了第一个 chunk，这本书会被重新建出来（get_or_create_collection）。
  async function handleRemove(id: string) {
    if (pendingNewBooks.includes(id)) {
      try {
        await deleteBook(id);
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 404)) {
          setError(e instanceof Error ? e.message : String(e));
          return;
        }
      }
      // 待导入书没走过 useBooks().remove()，那条路径里关窗口的逻辑覆盖
      // 不到这里——同名书重新建出来时，旧窗口还开着的话会直接被聚焦、
      // 显示删除前缓存的旧状态（比如已经加过的待导入文件列表）。
      await closeBookWindows(id);
      setPendingNewBooks((prev) => prev.filter((b) => b !== id));
      return;
    }
    // remove() 内部成功时自己会调 refresh()，这里不用再调一次——之前重复
    // 调用会在 remove() 刚把 409 错误存进 error 之后，被这里多余的 refresh()
    // 自己的成功分支（GET /books 本身不会失败）把 error 立刻清空，错误提示
    // 还没来得及显示就没了。
    await remove(id);
  }

  const allBooks = [...books, ...pendingNewBooks.filter((id) => !books.includes(id))];

  return (
    <div className={styles.grid}>
      {allBooks.map((bookId) => (
        <BookCard
          key={bookId}
          bookId={bookId}
          busy={status.busy}
          activity={bookActivity(status, bookId)}
          onRemove={handleRemove}
          onRename={rename}
        />
      ))}
      <button className={styles.addTile} aria-label="新建书" onClick={() => setCreating(true)}>
        +
      </button>
      {creating && (
        <NewBookDialog
          existingBookIds={allBooks}
          onCreate={handleCreate}
          onCancel={() => setCreating(false)}
        />
      )}
      {error && <Toast onDismiss={() => setError(null)}>{error}</Toast>}
    </div>
  );
}
