import { useStatus } from "../hooks/useStatus";
import { useImportProgress } from "../hooks/useImportProgress";
import { BookGrid } from "../components/BookGrid";

export function HomeView() {
  const { unreachable } = useStatus();
  useImportProgress();

  return (
    <div>
      <h1>BookAgent</h1>
      {unreachable && <div role="alert">服务未响应，重试中…</div>}
      {!unreachable && <BookGrid />}
    </div>
  );
}
