import { useState } from "react";
import { ConversationList } from "../components/ConversationList";
import { ChatPanel } from "../components/ChatPanel";
import { useStatus } from "../hooks/useStatus";

interface ChatViewProps {
  bookId: string;
}

export function ChatView({ bookId }: ChatViewProps) {
  const { status } = useStatus();
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);

  return (
    <div>
      <ConversationList
        bookId={bookId}
        selectedId={selectedConversation}
        onSelect={setSelectedConversation}
      />
      {selectedConversation && (
        <ChatPanel bookId={bookId} conversationId={selectedConversation} status={status} />
      )}
    </div>
  );
}
