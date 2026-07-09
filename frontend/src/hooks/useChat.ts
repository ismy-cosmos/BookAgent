import { useCallback, useEffect, useState } from "react";
import type { AskResponse, ChatTurnRecord } from "../api/types";
import { ask, getConversation } from "../api/client";

export function useChat(bookId: string, conversationId: string) {
  const [history, setHistory] = useState<ChatTurnRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setHistory([]);
    setError(null);

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
    async (question: string): Promise<AskResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await ask(bookId, conversationId, question);
        setHistory((prev) => [
          ...prev,
          { question, answer: result.answer, citations: result.citations },
        ]);
        return result;
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        return null;
      } finally {
        setLoading(false);
      }
    },
    [bookId, conversationId],
  );

  return { history, loading, error, send };
}
