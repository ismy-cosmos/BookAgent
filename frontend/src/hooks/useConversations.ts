import { useCallback, useEffect, useState } from "react";
import type { ConversationSummary } from "@/api/types";
import { createConversation, deleteConversation, listConversations } from "@/api/client";

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

  const create = useCallback(async (): Promise<string | null> => {
    try {
      const record = await createConversation(bookId);
      await refresh();
      return record.id;
    } catch {
      return null;
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
