import { useCallback, useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { ConversationList } from "../components/ConversationList";
import { ChatPanel } from "../components/ChatPanel";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { useStatus } from "../hooks/useStatus";
import { useConversations } from "../hooks/useConversations";
import { installQuitConfirmation } from "../quitConfirmation";
import styles from "../ChatWindow.module.css";

interface ChatViewProps {
  bookId: string;
}

export function ChatView({ bookId }: ChatViewProps) {
  const { status } = useStatus();
  const { conversations, create, remove, refresh } = useConversations(bookId);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  // 这个窗口自己的对话是不是在等回复——只看这个，不看全局 status.busy。
  // 别的书在忙不该拦这本书聊天窗口的关闭，只有这本书自己的问题还没回来
  // 时关闭才需要提醒。ref 而非 state：只在 close-requested 触发那一刻
  // 读一次最新值，不需要为它专门触发重渲染。
  const pendingRef = useRef(false);
  const [confirmingClose, setConfirmingClose] = useState(false);

  const handlePendingChange = useCallback((pending: boolean) => {
    pendingRef.current = pending;
  }, []);

  useEffect(() => {
    // 跟 HomeView 同一套 cancelled 标记处理 StrictMode 的 mount→cleanup→
    // 再 mount：installQuitConfirmation 是异步的，第一次 cleanup 跑的时候
    // promise 可能还没 resolve，直接反注册这次的监听器，不留下两个监听器
    // 同时活着。
    let cancelled = false;
    let unlisten: (() => void) | undefined;
    installQuitConfirmation(() => pendingRef.current, () => setConfirmingClose(true)).then((fn) => {
      if (cancelled) {
        fn();
      } else {
        unlisten = fn;
      }
    });
    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, []);

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
          onPendingChange={handlePendingChange}
        />
      )}
      {confirmingClose && (
        <ConfirmDialog
          message="有对话正在处理中，确定要关闭吗？"
          confirmLabel="确定关闭"
          onConfirm={() => {
            setConfirmingClose(false);
            getCurrentWindow().destroy();
          }}
          onCancel={() => setConfirmingClose(false)}
        />
      )}
    </div>
  );
}
