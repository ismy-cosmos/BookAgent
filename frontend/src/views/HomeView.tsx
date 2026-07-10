import { useStatus } from "../hooks/useStatus";
import { useImportProgress } from "../hooks/useImportProgress";
import { BookGrid } from "../components/BookGrid";
import { GlobalImportCapsule } from "../components/GlobalImportCapsule";
import { pauseImport } from "../api/client";

export function HomeView() {
  const { unreachable } = useStatus();
  const { progress } = useImportProgress();

  return (
    <div>
      <h1>BookAgent</h1>
      {unreachable && <div role="alert">服务未响应，重试中…</div>}
      {!unreachable && <BookGrid />}
      <GlobalImportCapsule progress={progress} onPause={() => pauseImport().catch(() => {})} />
    </div>
  );
}
