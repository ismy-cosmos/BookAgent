import { useCallback, useEffect, useState } from "react";
import type { ChatTurnRecord } from "@/api/types";
import { ask, getConversation } from "@/api/client";

export function useChat(bookId: string, conversationId: string) {
  const [history, setHistory] = useState<ChatTurnRecord[]>([]);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setHistory([]);
    setError(null);
    setPendingQuestion(null);

    (async () => {
      try {
        const record = await getConversation(bookId, conversationId);
        if (!cancelled) setHistory(record.turns);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [bookId, conversationId]);

  const send = useCallback(
    async (question: string): Promise<boolean> => {
      setPendingQuestion(question);
      setError(null);
      try {
        const result = await ask(bookId, conversationId, question);
        setHistory((prev) => [
          ...prev,
          {
            question,
            answer: result.answer,
            citations: result.citations,
            used_calculate: result.used_calculate,
            attempted_retrieve: result.attempted_retrieve,
          },
        ]);
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        return false;
      } finally {
        setPendingQuestion(null);
      }
    },
    [bookId, conversationId],
  );

  const clearError = useCallback(() => setError(null), []);

  return { history, pendingQuestion, error, send, clearError };
}
