import { useState } from "react";
import { Modal } from "./Modal";
import styles from "../Modal.module.css";

interface NewBookDialogProps {
  existingBookIds: string[];
  onCreate: (bookId: string) => void;
  onCancel: () => void;
}

export function NewBookDialog({ existingBookIds, onCreate, onCancel }: NewBookDialogProps) {
  const [bookId, setBookId] = useState("");
  const trimmedId = bookId.trim();
  const isDuplicate = trimmedId !== "" && existingBookIds.includes(trimmedId);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!trimmedId || isDuplicate) return;
    onCreate(trimmedId);
  }

  return (
    <Modal onDismiss={onCancel}>
      <form onSubmit={handleSubmit}>
        <p>新建书</p>
        <div className={styles.inputRow}>
          {isDuplicate && <span className={styles.duplicateWarning}>书名已存在</span>}
        </div>
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
          <button type="submit" className={styles.primaryButton} disabled={!trimmedId || isDuplicate}>
            确定
          </button>
        </div>
      </form>
    </Modal>
  );
}
