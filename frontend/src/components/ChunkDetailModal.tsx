import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChunkDetail } from "../api/types";
import { getChunk } from "../api/client";
import { Modal } from "./Modal";
import { Toast } from "./Toast";
import styles from "../ChunkDetailModal.module.css";

interface ChunkDetailModalProps {
  bookId: string;
  chunkId: string | null;
  onClose: () => void;
}

function formatTime(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatLocation(detail: ChunkDetail): string | null {
  if (detail.page_start != null) {
    return detail.page_end != null && detail.page_end !== detail.page_start
      ? `第 ${detail.page_start}–${detail.page_end} 页`
      : `第 ${detail.page_start} 页`;
  }
  if (detail.start_sec != null && detail.end_sec != null) {
    return `${formatTime(detail.start_sec)}–${formatTime(detail.end_sec)}`;
  }
  return null;
}

export function ChunkDetailModal({ bookId, chunkId, onClose }: ChunkDetailModalProps) {
  const [detail, setDetail] = useState<ChunkDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDetail(null);
    setError(null);
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
    <Modal onDismiss={onClose} cardClassName={styles.card}>
      {detail && (
        <>
          <div className={styles.head}>
            <div>
              <div className={styles.source}>{detail.source_file}</div>
              {formatLocation(detail) && <div className={styles.location}>{formatLocation(detail)}</div>}
            </div>
            <button className={styles.close} aria-label="关闭" onClick={onClose}>
              ✕
            </button>
          </div>
          <blockquote className={styles.body}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{detail.content}</ReactMarkdown>
          </blockquote>
        </>
      )}
      {error && (
        <Toast position="top-center" onDismiss={() => setError(null)}>
          {error}
        </Toast>
      )}
    </Modal>
  );
}
