import { useEffect, useState } from "react";
import type { ChunkDetail } from "../api/types";
import { getChunk } from "../api/client";

interface ChunkDetailModalProps {
  bookId: string;
  chunkId: string | null;
  onClose: () => void;
}

export function ChunkDetailModal({ bookId, chunkId, onClose }: ChunkDetailModalProps) {
  const [detail, setDetail] = useState<ChunkDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!chunkId) return;
    let cancelled = false;

    (async () => {
      try {
        const result = await getChunk(bookId, chunkId);
        if (!cancelled) setDetail(result);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [bookId, chunkId]);

  if (!chunkId) return null;

  return (
    <div role="dialog" aria-modal="true" aria-label="引用原文">
      {detail && (
        <>
          <p><strong>来源文件：</strong>{detail.source_file}</p>
          {detail.page_start != null && (
            <p><strong>页码：</strong>{detail.page_start}{detail.page_end !== detail.page_start ? `-${detail.page_end}` : ""}</p>
          )}
          {detail.start_sec != null && <p><strong>时段：</strong>{detail.start_sec}s-{detail.end_sec}s</p>}
          <blockquote>{detail.content}</blockquote>
        </>
      )}
      {error && <p role="alert">{error}</p>}
      <button onClick={onClose}>关闭</button>
    </div>
  );
}
