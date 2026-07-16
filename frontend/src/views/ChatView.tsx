import { useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { ConversationList } from "../components/ConversationList";
import { ChatPanel } from "../components/ChatPanel";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { bookActivity } from "../bookActivity";
import { useStatus } from "../hooks/useStatus";
import { useConversations } from "../hooks/useConversations";
import { installQuitConfirmation } from "../quitConfirmation";
import type { Status } from "../api/types";
import styles from "../ChatWindow.module.css";

interface ChatViewProps {
  bookId: string;
}

export function ChatView({ bookId }: ChatViewProps) {
  const { status } = useStatus();
  const { conversations, create, remove, refresh } = useConversations(bookId);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const statusRef = useRef<Status>(status);
  statusRef.current = status;
  const [confirmingClose, setConfirmingClose] = useState(false);

  useEffect(() => {
    // 跟 HomeView 同一套 cancelled 标记处理 StrictMode 的 mount→cleanup→
    // 再 mount：installQuitConfirmation 是异步的，第一次 cleanup 跑的时候
    // promise 可能还没 resolve，直接反注册这次的监听器，不留下两个监听器
    // 同时活着。
    // "这本书是不是有问题在等"改读共享 bookActivity(status, bookId)（跟
    // BookCard/FileList 等组件同一个权威来源），不是 ChatPanel/useChat 内部
    // 那份本地 pendingQuestion——本地状态会在切换对话时被清空，即使上一个
    // 对话的请求其实还在后台跑着，共享状态不受这个影响。
    let cancelled = false;
    let unlisten: (() => void) | undefined;
    installQuitConfirmation(
      () => bookActivity(statusRef.current, bookId) === "answering",
      () => setConfirmingClose(true),
    ).then((fn) => {
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
  }, [bookId]);

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
