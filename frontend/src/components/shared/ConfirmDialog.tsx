import { Modal } from "./Modal";
import styles from "./Modal.module.css";

interface ConfirmDialogProps {
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  message,
  confirmLabel = "确认删除",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal onDismiss={onCancel}>
      <p>{message}</p>
      <div className={styles.actions}>
        <button className={styles.secondaryButton} onClick={onCancel}>
          取消
        </button>
        <button className={styles.dangerButton} onClick={onConfirm}>
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
