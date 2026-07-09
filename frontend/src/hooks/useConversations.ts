import { useCallback, useEffect, useState } from "react";
import type { ConversationSummary } from "../api/types";
import { createConversation, deleteConversation, listConversations } from "../api/client";

export function useConversations(bookId: string) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  const refresh = useCallback(async () => {
    try {
      const result = await listConversations(bookId);
      setConversations(result.conversations);
    } catch {
      // noop
    }
  }, [bookId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = useCallback(async () => {
    try {
      await createConversation(bookId);
      await refresh();
    } catch {
      // noop
    }
  }, [bookId, refresh]);

  const remove = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(bookId, id);
        await refresh();
      } catch {
        // noop
      }
    },
    [bookId, refresh],
  );

  return { conversations, refresh, create, remove };
}
