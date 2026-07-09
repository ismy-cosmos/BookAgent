import { useState } from "react";
import { useChat } from "../hooks/useChat";
import type { Status } from "../api/types";

interface ChatPanelProps {
  bookId: string;
  conversationId: string;
  status: Status;
}

export function ChatPanel({ bookId, conversationId, status }: ChatPanelProps) {
  const { history, loading, send } = useChat(bookId, conversationId);
  const [input, setInput] = useState("");
  const disabled = status.busy;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    await send(q);
  }

  return (
    <div>
      <h3>问答</h3>
      <div>
        {history.map((turn, i) => (
          <div key={i}>
            <p><strong>Q:</strong> {turn.question}</p>
            <p><strong>A:</strong> {turn.answer}</p>
          </div>
        ))}
        {loading && <p>思考中…</p>}
      </div>
      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={disabled ? "正在导入书籍，请稍后…" : "输入问题"}
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || !input.trim() || loading}>
          发送
        </button>
      </form>
    </div>
  );
}
