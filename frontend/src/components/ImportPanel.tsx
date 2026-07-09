import { useEffect, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { cancelImport, pauseImport, resumeImport, submitImport } from "../api/client";
import { useStagedFiles } from "../hooks/useStagedFiles";
import { stageText } from "../importProgressText";
import { ImportCompletionToast } from "./ImportCompletionToast";
import type { LastResult, ProgressResponse } from "../api/types";

// 跟后端 scripts/ingest.py 的 _ALL_EXTS 保持一致
const SUPPORTED_EXTENSIONS = ["pdf", "epub", "mp3", "wav", "flac", "png", "jpg", "jpeg", "svg"];

interface ImportPanelProps {
  bookId: string;
  progress: ProgressResponse | null;
}

export function ImportPanel({ bookId, progress }: ImportPanelProps) {
  const { files, error, refresh, add, remove } = useStagedFiles(bookId);
  const [queuedTaskId, setQueuedTaskId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const importingThisBook = !!progress?.busy && progress.book_id === bookId;

  // 导入进行中每个文件成功入库会从待导入列表消失（后端行为）——
  // 随进度变化（文件边界/任务结束）重新拉取列表。单独盯 last_result 的内容
  // （而非 busy）是因为导入耗时可能短于轮询间隔，busy 从未被前端观察到变
  // true 过，此时只有 last_result 的内容会变化。
  const lastResultKey = JSON.stringify(progress?.last_result);
  useEffect(() => {
    refresh();
  }, [refresh, progress?.busy, progress?.progress?.current_file, lastResultKey]);

  // 自己排队的任务开始处理后，"取消排队"不再适用
  useEffect(() => {
    if (importingThisBook) setQueuedTaskId(null);
  }, [importingThisBook]);

  async function handleAddFiles() {
    const picked = await open({
      multiple: true,
      filters: [{ name: "支持的文件", extensions: SUPPORTED_EXTENSIONS }],
    });
    if (!picked) return;
    await add(Array.isArray(picked) ? picked : [picked]);
  }

  async function handleSubmit() {
    try {
      const wasBusyElsewhere = !!progress?.busy && progress.book_id !== bookId;
      const result = await submitImport(bookId);
      if (wasBusyElsewhere) setQueuedTaskId(result.task_id);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleCancelQueued() {
    if (!queuedTaskId) return;
    try {
      await cancelImport(queuedTaskId);
      setQueuedTaskId(null);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : String(e));
    }
  }

  const lastResult =
    progress && !progress.busy && progress.last_result?.book_id === bookId
      ? progress.last_result
      : null;

  // 弹窗自己不会随 lastResult 消失而消失（消失了没法读），所以用一个 ref
  // 记住"这份结果是不是已经弹过"，避免每次轮询都重新弹出同一份结果。
  const [toastResult, setToastResult] = useState<LastResult | null>(null);
  const shownResultKeyRef = useRef<string | null>(null);
  useEffect(() => {
    const key = JSON.stringify(lastResult);
    if (lastResult && key !== shownResultKeyRef.current) {
      shownResultKeyRef.current = key;
      setToastResult(lastResult);
    }
  }, [lastResult]);

  return (
    <section aria-label="导入管理">
      <h3>待导入</h3>
      <button onClick={handleAddFiles}>添加文件</button>
      <ul>
        {files.map((path) => (
          <li key={path}>
            {path}
            <button aria-label={`移除 ${path}`} onClick={() => remove(path)}>
              ×
            </button>
          </li>
        ))}
      </ul>
      <button disabled={files.length === 0 || importingThisBook} onClick={handleSubmit}>
        开始导入
      </button>
      {queuedTaskId && !importingThisBook && (
        <button onClick={handleCancelQueued}>取消排队</button>
      )}

      {importingThisBook && progress?.progress && (
        <div role="status">
          <span>{stageText(progress.progress)}</span>
          {progress.pause_requested ? (
            <button disabled>正在暂停…</button>
          ) : (
            <button onClick={() => pauseImport().catch(() => {})}>暂停</button>
          )}
        </div>
      )}

      {progress && !progress.busy && progress.pause_requested && (
        <div role="status">
          <span>已暂停</span>
          <button onClick={() => resumeImport().catch(() => {})}>恢复</button>
        </div>
      )}

      {toastResult && (
        <ImportCompletionToast
          result={toastResult}
          onDismiss={() => setToastResult(null)}
        />
      )}

      {(error ?? actionError) && <p role="alert">{error ?? actionError}</p>}
    </section>
  );
}
