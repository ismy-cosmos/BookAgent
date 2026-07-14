import styles from "../Modal.module.css";

interface ModalProps {
  children: React.ReactNode;
  onDismiss?: () => void;
  // 默认用 styles.card（320px，ConfirmDialog/ErrorModal/NewBookDialog 在用）；
  // 传了就整个替换掉，不是叠加——不同弹窗宽度差异大（比如 ChunkDetailModal
  // 要 420px 装下引用原文），叠加两个类名互相覆盖同一个 width 属性靠样式表
  // 声明顺序决定谁赢，容易出问题，不如让调用方自己决定要哪一套卡片样式。
  cardClassName?: string;
}

export function Modal({ children, onDismiss, cardClassName }: ModalProps) {
  return (
    <div className={styles.backdrop} onClick={onDismiss}>
      <div
        className={cardClassName ?? styles.card}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
