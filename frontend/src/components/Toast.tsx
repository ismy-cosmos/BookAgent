import type { ReactNode } from "react";
import styles from "../Toast.module.css";

interface ToastProps {
  message?: string;
  children?: ReactNode;
  position?: "top-right" | "top-center";
  onDismiss?: () => void;
}

export function Toast({ message, children, position = "top-right", onDismiss }: ToastProps) {
  const positionClass = position === "top-center" ? styles.topCenter : styles.topRight;
  return (
    <div className={`${styles.toast} ${positionClass}`} role="alert">
      <div className={styles.content}>{children ?? message}</div>
      {onDismiss && (
        <button className={styles.close} aria-label="关闭" onClick={onDismiss}>
          ×
        </button>
      )}
    </div>
  );
}
