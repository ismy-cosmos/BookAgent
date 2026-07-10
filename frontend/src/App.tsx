import { HomeView } from "./views/HomeView";
import { ImportView } from "./views/ImportView";
import { ChatView } from "./views/ChatView";

function App() {
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  const bookId = params.get("book");

  if (view === "import" && bookId) {
    return <ImportView bookId={bookId} />;
  }
  if (view === "chat" && bookId) {
    return <ChatView bookId={bookId} />;
  }
  return <HomeView />;
}

export default App;
