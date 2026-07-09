import { useState } from "react";
import { BookList } from "./components/BookList";
import { FileList } from "./components/FileList";
import { ConversationList } from "./components/ConversationList";
import { ChatPanel } from "./components/ChatPanel";
import { ImportPanel } from "./components/ImportPanel";
import { ImportStatusBar } from "./components/ImportStatusBar";
import { useStatus } from "./hooks/useStatus";
import { useImportProgress } from "./hooks/useImportProgress";

function App() {
  const { status, unreachable } = useStatus();
  const { progress } = useImportProgress();
  const [selectedBook, setSelectedBook] = useState<string | null>(null);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);

  const selectBook = (bookId: string) => {
    setSelectedBook(bookId);
    setSelectedConversation(null);
  };

  return (
    <div>
      <h1>BookAgent</h1>
      {unreachable && <div role="alert">服务未响应，重试中…</div>}
      <ImportStatusBar progress={progress} onJumpToBook={selectBook} />

      {!unreachable && (
        <BookList status={status} selectedBook={selectedBook} onSelectBook={selectBook} />
      )}

      {selectedBook && <ImportPanel bookId={selectedBook} progress={progress} />}

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
