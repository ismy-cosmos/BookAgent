import styles from "../Modal.module.css";

interface ModalProps {
  children: React.ReactNode;
  onDismiss?: () => void;
}

export function Modal({ children, onDismiss }: ModalProps) {
  return (
    <div className={styles.backdrop} onClick={onDismiss}>
      <div
        className={styles.card}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
