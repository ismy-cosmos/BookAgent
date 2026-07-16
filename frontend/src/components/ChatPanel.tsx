import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChat } from "../hooks/useChat";
import { citationLabel } from "../citationLabel";
import { stripAnswerTags } from "../stripAnswerTags";
import { ChunkDetailModal } from "./ChunkDetailModal";
import { Toast } from "./Toast";
import type { Status } from "../api/types";
import styles from "../ChatWindow.module.css";

interface ChatPanelProps {
  bookId: string;
  conversationId: string;
  status: Status;
  onSent?: () => void;
}

export function ChatPanel({ bookId, conversationId, status, onSent }: ChatPanelProps) {
  const { history, pendingQuestion, error, send, clearError } = useChat(bookId, conversationId);
  const [input, setInput] = useState("");
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // jsdom（测试环境）没有实现 scrollIntoView，连桩函数都没有——调用会
    // 直接抛 TypeError，不是空操作。真实浏览器/Tauri webview 里这个方法
    // 总是存在，只在测试环境需要这层判断。
    messagesEndRef.current?.scrollIntoView?.({ block: "end" });
  }, [history.length, pendingQuestion]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || pendingQuestion || status.busy) return;
    setInput("");
    const ok = await send(q);
    if (ok) {
      onSent?.();
    } else {
      setInput(q); // 失败时把问题文本还原回输入框，不用重打
    }
  }

  return (
    <div className={styles.chatColumn}>
      <div className={styles.messages}>
        {history.map((turn, i) => {
          const label = citationLabel(turn.citations, turn.attempted_retrieve ?? false);
          return (
            <div key={i}>
              <div className={`${styles.row} ${styles.rowQuestion}`}>
                <div className={`${styles.bubble} ${styles.bubbleQuestion}`}>{turn.question}</div>
              </div>
              <div className={`${styles.row} ${styles.rowAnswer}`}>
                <div className={styles.answerWrap}>
                  <div className={`${styles.bubble} ${styles.bubbleAnswer}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {stripAnswerTags(turn.answer)}
                    </ReactMarkdown>
                  </div>
                  {label.kind === "pills" ? (
                    <div className={styles.pills}>
                      {label.citations.map((c) => (
                        <button
                          key={c.chunk_id}
                          type="button"
                          className={styles.pill}
                          title={c.citation}
                          onClick={() => setSelectedChunkId(c.chunk_id)}
                        >
                          {c.citation}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <span className={styles.tagLabel}>{label.text}</span>
                  )}
                  {(turn.used_calculate ?? false) && (
                    <span className={styles.tagLabel}>已使用计算工具</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        {pendingQuestion && (
          <div>
            <div className={`${styles.row} ${styles.rowQuestion}`}>
              <div className={`${styles.bubble} ${styles.bubbleQuestion}`}>{pendingQuestion}</div>
            </div>
            <div className={`${styles.row} ${styles.rowAnswer}`}>
              <div className={styles.thinkingBubble} role="status" aria-label="思考中">
                <span className={styles.thinkingDot} />
                <span className={styles.thinkingDot} />
                <span className={styles.thinkingDot} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} className={styles.inputRow}>
        <input
          className={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入问题"
        />
        <button
          className={styles.sendButton}
          type="submit"
          disabled={status.busy || !input.trim() || !!pendingQuestion}
        >
          发送
        </button>
      </form>
      {error && (
        <Toast position="top-center" onDismiss={clearError}>
          {error}
        </Toast>
      )}
      <ChunkDetailModal bookId={bookId} chunkId={selectedChunkId} onClose={() => setSelectedChunkId(null)} />
    </div>
  );
}
