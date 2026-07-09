import { useConversations } from "../hooks/useConversations";

interface ConversationListProps {
  bookId: string;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ConversationList({ bookId, selectedId, onSelect }: ConversationListProps) {
  const { conversations, create, remove } = useConversations(bookId);

  return (
    <div>
      <h3>对话</h3>
      <button onClick={create}>新建对话</button>
      <ul>
        {conversations.map((c) => (
          <li key={c.id}>
            <button onClick={() => onSelect(c.id)} aria-current={c.id === selectedId}>
              {c.title}
            </button>
            <button onClick={() => remove(c.id)}>删除</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
