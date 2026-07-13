import type { ReactNode } from "react";
import styles from "../Toast.module.css";

interface ToastProps {
  children: ReactNode;
  variant?: "error" | "neutral";
  position?: "top-right" | "top-center";
  onDismiss?: () => void;
}

export function Toast({ children, variant = "error", position = "top-right", onDismiss }: ToastProps) {
  const positionClass = position === "top-center" ? styles.topCenter : styles.topRight;
  const variantClass = variant === "neutral" ? styles.neutral : styles.error;
  return (
    <div
      className={`${styles.toast} ${positionClass} ${variantClass}`}
      role={variant === "error" ? "alert" : "status"}
    >
      <div className={styles.content}>{children}</div>
      {onDismiss && (
        <button className={styles.close} aria-label="关闭" onClick={onDismiss}>
          ×
        </button>
      )}
    </div>
  );
}
