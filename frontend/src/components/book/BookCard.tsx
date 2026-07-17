import { useState } from "react";
import { openOrFocusWindow } from "@/windowManager";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import type { BookActivity } from "@/bookActivity";
import styles from "./BookCard.module.css";

interface BookCardProps {
  bookId: string;
  busy: boolean;
  activity: BookActivity;
  onRemove: (bookId: string) => void;
  onRename: (bookId: string, newBookId: string) => Promise<void>;
}

export function BookCard({ bookId, busy, activity, onRemove, onRename }: BookCardProps) {
  const [hovered, setHovered] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draftName, setDraftName] = useState(bookId);

  async function commitRename() {
    setEditing(false);
    if (draftName.trim() && draftName !== bookId) {
      try {
        await onRename(bookId, draftName.trim());
      } catch {
        setDraftName(bookId);
      }
    } else {
      setDraftName(bookId);
    }
  }

  return (
    <div
      className={styles.card}
      data-testid="book-card"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className={styles.cover}>
        {hovered && !editing && (
          <div className={styles.overlay}>
            <button
              className={styles.btnImport}
              onClick={() => openOrFocusWindow("import", bookId, bookId)}
            >
              导入文件
            </button>
            <button
              className={styles.btnChat}
              disabled={busy}
              onClick={() => openOrFocusWindow("chat", bookId, bookId)}
            >
              开始对话
            </button>
            <button
              className={styles.btnDelete}
              disabled={activity !== "idle"}
              onClick={() => setConfirmingDelete(true)}
            >
              删除丛书
            </button>
          </div>
        )}
      </div>
      {editing ? (
        <input
          className={styles.name}
          value={draftName}
          autoFocus
          onFocus={(e) => e.target.select()}
          onChange={(e) => setDraftName(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitRename();
            if (e.key === "Escape") {
              setDraftName(bookId);
              setEditing(false);
            }
          }}
        />
      ) : (
        <span
          className={styles.name}
          onDoubleClick={() => {
            setDraftName(bookId);
            setEditing(true);
          }}
        >
          {bookId}
        </span>
      )}
      {activity === "ingesting" && <span className={styles.badge}>导入中…</span>}
      {activity === "answering" && <span className={styles.badge}>对话中…</span>}
      {confirmingDelete && (
        <ConfirmDialog
          message={`确定要删除 '${bookId}' 吗？此操作不可恢复。`}
          onConfirm={() => {
            onRemove(bookId);
            setConfirmingDelete(false);
          }}
          onCancel={() => setConfirmingDelete(false)}
        />
      )}
    </div>
  );
}
