import type { ConversationSummary } from "../api/types";
import styles from "../ChatWindow.module.css";

interface ConversationListProps {
  conversations: ConversationSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRemove: (id: string) => void;
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  onCreate,
  onRemove,
}: ConversationListProps) {
  return (
    <nav className={styles.sidebar} aria-label="对话列表">
      <button className={styles.newConversation} onClick={onCreate} aria-label="新建对话">
        <span aria-hidden="true">＋</span>
        <span className={styles.newConversationLabel}>新对话</span>
      </button>
      <div className={styles.conversationList}>
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`${styles.conversationItem} ${c.id === selectedId ? styles.active : ""}`}
          >
            <button
              type="button"
              className={styles.conversationSelect}
              aria-current={c.id === selectedId}
              onClick={() => onSelect(c.id)}
            >
              <span className={styles.conversationTitle}>{c.title}</span>
            </button>
            <button type="button" className={styles.conversationDelete} onClick={() => onRemove(c.id)}>
              删除
            </button>
          </div>
        ))}
      </div>
    </nav>
  );
}
