import { ImportPanel } from "../components/ImportPanel";
import { FileList } from "../components/FileList";
import { useImportProgress } from "../hooks/useImportProgress";

interface ImportViewProps {
  bookId: string;
}

export function ImportView({ bookId }: ImportViewProps) {
  const { progress } = useImportProgress();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <ImportPanel bookId={bookId} progress={progress} />
      <FileList bookId={bookId} progress={progress} />
    </div>
  );
}
