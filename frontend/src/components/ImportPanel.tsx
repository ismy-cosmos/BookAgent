import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { cancelImport, pauseImport, resumeImport, submitImport } from "../api/client";
import { useStagedFiles } from "../hooks/useStagedFiles";
import type { ImportProgress, ProgressResponse } from "../api/types";

// 跟后端 scripts/ingest.py 的 _ALL_EXTS 保持一致
const SUPPORTED_EXTENSIONS = ["pdf", "epub", "mp3", "wav", "flac", "png", "jpg", "jpeg", "svg"];

export function stageText(p: ImportProgress): string {
  if (p.stage === "parsing") return `解析中 文件 ${p.current_file}/${p.total_files}`;
  if (p.stage === "vlm") return `图片描述 ${p.current_image}/${p.total_images}`;
  return "正在存储…";
}

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
  // 随进度变化（文件边界/任务结束）重新拉取列表
  useEffect(() => {
    refresh();
  }, [refresh, progress?.busy, progress?.progress?.current_file]);

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

      {lastResult && (
        <div role="status">
          {lastResult.error ? (
            <span>导入失败：{lastResult.error}</span>
          ) : (
            <>
              <span>
                导入完成：入库 {lastResult.total_chunks} 块
                {(lastResult.failures?.length ?? 0) > 0 &&
                  `，${lastResult.failures!.length} 个文件失败`}
                {(lastResult.not_attempted?.length ?? 0) > 0 &&
                  `，${lastResult.not_attempted!.length} 个文件未处理`}
              </span>
              {(lastResult.failures?.length ?? 0) > 0 && (
                <details>
                  <summary>查看失败详情</summary>
                  <ul>
                    {lastResult.failures!.map((f) => (
                      <li key={f.file}>
                        {f.file}：{f.error_message}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          )}
        </div>
      )}

      {(error ?? actionError) && <p role="alert">{error ?? actionError}</p>}
    </section>
  );
}
