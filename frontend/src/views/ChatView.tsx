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

  return (
    <div className={styles.window}>
      <ConversationList
        conversations={conversations}
        selectedId={selectedConversation}
        onSelect={setSelectedConversation}
        onCreate={create}
        onRemove={remove}
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
