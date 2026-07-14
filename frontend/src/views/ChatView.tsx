import { useState } from "react";
import { ConversationList } from "../components/ConversationList";
import { ChatPanel } from "../components/ChatPanel";
import { useStatus } from "../hooks/useStatus";
import { useConversations } from "../hooks/useConversations";
import styles from "../ChatWindow.module.css";

interface ChatViewProps {
  bookId: string;
}

export function ChatView({ bookId }: ChatViewProps) {
  const { status } = useStatus();
  const { conversations, create, remove, refresh } = useConversations(bookId);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);

  async function handleCreate() {
    const newId = await create();
    if (newId) setSelectedConversation(newId);
  }

  function handleRemove(id: string) {
    // 删的如果正好是当前正在看的对话，立刻清空右栏——不等网络请求
    // 结果，避免用户在已经被删掉的对话内容前不知道到底删没删成功。
    if (id === selectedConversation) setSelectedConversation(null);
    remove(id);
  }

  return (
    <div className={styles.window}>
      <ConversationList
        conversations={conversations}
        selectedId={selectedConversation}
        onSelect={setSelectedConversation}
        onCreate={handleCreate}
        onRemove={handleRemove}
      />
      {selectedConversation && (
        <ChatPanel
          bookId={bookId}
          conversationId={selectedConversation}
          status={status}
          onSent={refresh}
        />
      )}
    </div>
  );
}
