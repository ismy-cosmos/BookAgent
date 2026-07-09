import { useState } from "react";
import { BookList } from "./components/BookList";
import { FileList } from "./components/FileList";
import { ConversationList } from "./components/ConversationList";
import { ChatPanel } from "./components/ChatPanel";
import { useStatus } from "./hooks/useStatus";

function App() {
  const { status, unreachable } = useStatus();
  const [selectedBook, setSelectedBook] = useState<string | null>(null);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);

  return (
    <div>
      <h1>BookAgent</h1>
      {unreachable && <div role="alert">服务未响应，重试中…</div>}

      <BookList
        status={status}
        selectedBook={selectedBook}
        onSelectBook={(bookId) => {
          setSelectedBook(bookId);
          setSelectedConversation(null);
        }}
      />

      {selectedBook && <FileList bookId={selectedBook} />}

      {selectedBook && (
        <ConversationList
          bookId={selectedBook}
          selectedId={selectedConversation}
          onSelect={setSelectedConversation}
        />
      )}

      {selectedBook && selectedConversation && (
        <ChatPanel bookId={selectedBook} conversationId={selectedConversation} status={status} />
      )}
    </div>
  );
}

export default App;
