import type { ProgressResponse } from "../api/types";
import { stageText } from "../importProgressText";

interface ImportStatusBarProps {
  progress: ProgressResponse | null;
  onJumpToBook: (bookId: string) => void;
}

export function ImportStatusBar({ progress, onJumpToBook }: ImportStatusBarProps) {
  if (!progress?.busy || !progress.book_id) return null;
  const bookId = progress.book_id;
  return (
    <button onClick={() => onJumpToBook(bookId)}>
      正在导入《{bookId}》：{progress.progress ? stageText(progress.progress) : ""}
      {progress.pause_requested && "（正在暂停…）"}
    </button>
  );
}
