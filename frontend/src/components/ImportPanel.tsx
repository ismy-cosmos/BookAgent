import { useCallback, useEffect, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { dirname } from "@tauri-apps/api/path";
import { cancelImport, pauseImport, submitImport } from "../api/client";
import { bookActivity } from "../bookActivity";
import { useStagedFiles } from "../hooks/useStagedFiles";
import { stageText } from "../importProgressText";
import { ImportCompletionToast } from "./ImportCompletionToast";
import { Toast } from "@/components/shared/Toast";
import type { ImportProgress, LastResult, ProgressResponse } from "../api/types";
import styles from "../ImportFileList.module.css";

// 跟后端 scripts/ingest.py 的 _ALL_EXTS 保持一致
const SUPPORTED_EXTENSIONS = ["pdf", "epub", "mp3", "wav", "flac", "png", "jpg", "jpeg", "svg"];

// 文件选择器默认打开上次选文件所在的目录，全局共享（不分 book）——用户
// 一般连续导入同一批资料时素材都在同一个文件夹，不需要每本书单独记一份。
const LAST_IMPORT_DIR_KEY = "bookagent:lastImportDir";

interface ImportPanelProps {
  bookId: string;
  progress: ProgressResponse | null;
}

export function ImportPanel({ bookId, progress }: ImportPanelProps) {
  const { files, error, refresh, add, remove, setError } = useStagedFiles(bookId);
  const [queuedTaskId, setQueuedTaskId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const activity = bookActivity(progress, bookId);
  const importingThisBook = activity === "ingesting";
  // 已提交但还没轮到处理——这本书的批次不能再改，只能整批只读+取消排队。
  const isQueued = !!queuedTaskId && !importingThisBook;
  const isReadOnly = importingThisBook || isQueued;

  // 全局暂停一旦被触发（不一定是这本书自己点的——任何书暂停都会顺手取消
  // 所有排队中的任务），这本书如果排着队，它在后端的任务已经被取消了，
  // 本地这份 queuedTaskId 要跟着清掉，UI 才不会卡在一个已经不存在的
  // "排队中"状态里。暂停没有"恢复"，界面直接退回正常待导入态即可。
  useEffect(() => {
    if (progress?.pause_requested) setQueuedTaskId(null);
  }, [progress?.pause_requested]);

  // 记住这本书正在导入期间收到的最后一次真实进度快照——任务结束（不管
  // 是正常完成还是被暂停打断）那一刻后端就把 progress 清空了，没有这份
  // 记录的话，"已暂停"弹窗没法知道暂停生效前具体停在哪个阶段、还剩多少
  // 没处理（阶段2 中断只知道"文件"，不知道"图片"，得从这份快照里算）。
  const lastLiveProgressRef = useRef<ImportProgress | null>(null);
  useEffect(() => {
    if (importingThisBook && progress?.progress) {
      lastLiveProgressRef.current = progress.progress;
    }
  }, [importingThisBook, progress?.progress]);

  // 导入进行中每个文件成功入库会从待导入列表消失（后端行为）——
  // 随进度变化（文件边界/任务结束）重新拉取列表。单独盯 last_result 的内容
  // （而非 busy）是因为导入耗时可能短于轮询间隔，busy 从未被前端观察到变
  // true 过，此时只有 last_result 的内容会变化。盯的是 activity 而不是
  // 全局 progress?.busy——跟 FileList.tsx 同一个模式，别的书忙不忙、这本书
  // 自己有没有被问问题，都不该触发这本书待导入列表的多余刷新。
  //
  // 挂载那一刻 useStagedFiles 自己已经拉过一次了，这里跳过第一次运行，
  // 避免挂载瞬间重复打两次 listStagedFiles。
  const lastResultKey = JSON.stringify(progress?.last_result);
  const isFirstRender = useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    refresh();
  }, [refresh, activity, progress?.progress?.current_file, lastResultKey]);

  // 自己排队的任务开始处理后，"取消排队"不再适用
  useEffect(() => {
    if (importingThisBook) setQueuedTaskId(null);
  }, [importingThisBook]);

  async function handleAddFiles() {
    const picked = await open({
      multiple: true,
      defaultPath: localStorage.getItem(LAST_IMPORT_DIR_KEY) ?? undefined,
      filters: [{ name: "支持的文件", extensions: SUPPORTED_EXTENSIONS }],
    });
    if (!picked) return;
    const paths = Array.isArray(picked) ? picked : [picked];
    localStorage.setItem(LAST_IMPORT_DIR_KEY, await dirname(paths[0]));
    await add(paths);
  }

  async function handleSubmit() {
    try {
      const wasBusy = !!progress?.busy;
      const result = await submitImport(bookId);
      if (wasBusy) setQueuedTaskId(result.task_id);
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
    progress && activity !== "ingesting" && progress.last_result?.book_id === bookId
      ? progress.last_result
      : null;

  // 弹窗自己不会随 lastResult 消失而消失（消失了没法读），所以用一个 ref
  // 记住"这份结果是不是已经弹过"，避免每次轮询都重新弹出同一份结果。
  // 这份"已弹过"记录还落一份到 localStorage（按 book 分开存）：窗口关掉
  // 重开是组件重新 mount，内存态会丢，但后端 last_result 还在，不落盘的话
  // 同一份结果会在重开窗口时再弹一次。
  //
  // 去重键用 task_id，不能用内容本身（真实 bug）：暂停发生在文件还没
  // 开始处理之前时，重新提交同一批文件产生的结果内容会完全相同
  // （book_id/not_attempted 都一样），拿内容去重会把第二次真实发生的
  // 结果误判成"已经弹过的旧结果"吞掉。task_id 每次 enqueue 都不同。
  const shownResultStorageKey = `bookagent:importToastShown:${bookId}`;
  const [toastResult, setToastResult] = useState<LastResult | null>(null);
  const [pausedAtProgress, setPausedAtProgress] = useState<ImportProgress | null>(null);
  const shownTaskIdRef = useRef<string | null>(
    localStorage.getItem(shownResultStorageKey),
  );
  useEffect(() => {
    if (lastResult && lastResult.task_id !== shownTaskIdRef.current) {
      shownTaskIdRef.current = lastResult.task_id ?? null;
      if (lastResult.task_id) localStorage.setItem(shownResultStorageKey, lastResult.task_id);
      setToastResult(lastResult);
      setPausedAtProgress(lastLiveProgressRef.current);
    }
  }, [lastResult, shownResultStorageKey]);

  // 稳定的引用：ImportCompletionToast 内部拿它当 useEffect 依赖来控制自动
  // 消失的计时器，如果每次渲染都传一个新的内联函数，计时器会跟着轮询
  // （每次渲染）反复清掉重开，永远攒不够 6 秒，弹窗就变成"不会自动消失"。
  const dismissToast = useCallback(() => setToastResult(null), []);

  return (
    <section aria-label="导入管理">
      <h3 className={styles.heading}>待导入</h3>
      {files.length > 0 && (
        <ul className={styles.list}>
          {files.map((path) => (
            <li key={path} className={styles.row}>
              <span className={styles.filename}>{path}</span>
              {!isQueued && (
                <button
                  className={styles.removeAction}
                  disabled={importingThisBook}
                  aria-label={`移除 ${path}`}
                  onClick={() => remove(path)}
                >
                  {importingThisBook ? "导入中" : "移除"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* 待导入 / 正在导入：添加文件 + 开始导入 */}
      {!isQueued && (
        <div className={styles.btnRow}>
          <button className={styles.btnSecondary} disabled={isReadOnly} onClick={handleAddFiles}>
            添加文件
          </button>
          <button
            className={styles.btnBlue}
            disabled={files.length === 0 || isReadOnly}
            onClick={handleSubmit}
          >
            开始导入
          </button>
        </div>
      )}

      {/* 排队中：只有取消排队 */}
      {isQueued && (
        <div className={styles.btnRow}>
          <button className={styles.btnSecondary} onClick={handleCancelQueued}>
            取消排队
          </button>
        </div>
      )}

      {/* 正在导入：进度 + 暂停 */}
      {importingThisBook && progress?.progress && (
        <div role="status">
          <p className={styles.progressText}>{stageText(progress.progress)}</p>
          <div className={styles.btnRow}>
            {progress.pause_requested ? (
              <button className={styles.btnSecondary} disabled>
                正在暂停…
              </button>
            ) : (
              <button className={styles.btnRed} onClick={() => pauseImport().catch(() => {})}>
                暂停
              </button>
            )}
          </div>
        </div>
      )}

      {toastResult && (
        <ImportCompletionToast
          result={toastResult}
          pausedAtProgress={pausedAtProgress}
          onDismiss={dismissToast}
        />
      )}

      {(error ?? actionError) && (
        <Toast
          position="top-center"
          onDismiss={() => {
            setError(null);
            setActionError(null);
          }}
        >
          {error ?? actionError}
        </Toast>
      )}
    </section>
  );
}
