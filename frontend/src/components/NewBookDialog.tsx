import { useState } from "react";
import { Modal } from "./Modal";
import styles from "../Modal.module.css";

interface NewBookDialogProps {
  onCreate: (bookId: string) => void;
  onCancel: () => void;
}

export function NewBookDialog({ onCreate, onCancel }: NewBookDialogProps) {
  const [bookId, setBookId] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const id = bookId.trim();
    if (!id) return;
    onCreate(id);
  }

  return (
    <Modal onDismiss={onCancel}>
      <form onSubmit={handleSubmit}>
        <p>新建书</p>
        <input
          className={styles.input}
          aria-label="新书 book_id"
          placeholder="输入 book_id"
          value={bookId}
          onChange={(e) => setBookId(e.target.value)}
          autoFocus
        />
        <div className={styles.actions}>
          <button type="button" className={styles.secondaryButton} onClick={onCancel}>
            取消
          </button>
          <button type="submit" className={styles.primaryButton} disabled={!bookId.trim()}>
            确定
          </button>
        </div>
      </form>
    </Modal>
  );
}
