from __future__ import annotations
import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ImportTask:
    task_id: str
    book_id: str
    file_paths: list[str]


# (book_id, file_paths, should_pause, report_progress) -> 任务结果摘要（None 则不存档）
ProcessorFn = Callable[
    [str, list[str], Callable[[], bool], Callable[[dict], None]],
    Optional[dict],
]


class ImportQueue:
    def __init__(self, processor: ProcessorFn) -> None:
        self._processor = processor
        self._queue: "queue.Queue[ImportTask]" = queue.Queue()
        self._lock = threading.Lock()
        self._current_task: Optional[ImportTask] = None
        self._queued_tasks: dict[str, ImportTask] = {}
        self._cancelled_ids: set[str] = set()
        self._pause_event = threading.Event()
        self._progress: Optional[dict] = None
        self._last_result: Optional[dict] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def enqueue(self, book_id: str, file_paths: list[str]) -> str:
        task = ImportTask(task_id=uuid.uuid4().hex[:12], book_id=book_id, file_paths=file_paths)
        # _queued_tasks 登记和真正入队必须是同一个原子操作：分两步的话，
        # 中间有个缝隙——book_has_pending_or_active_task() 已经能查到这个
        # 任务，但 worker 线程实际上还拿不到它。self._queue 是无界队列，
        # put() 不会阻塞，锁内调用没有死锁风险。
        with self._lock:
            self._queued_tasks[task.task_id] = task
            self._queue.put(task)
        return task.task_id

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._queued_tasks:
                del self._queued_tasks[task_id]
                self._cancelled_ids.add(task_id)
                return True
            return False

    def request_pause(self) -> None:
        """暂停当前任务：在文件/图片边界提前收尾（run_ingest 里的
        should_pause 检查点）。同时把队列里排着的其他任务全部取消——暂停是
        "停下来，用户自己决定后续导入顺序"的决定性动作，不是"当前任务停一下，
        排队的书自动接着处理"；要哪本书继续导入，用户自己重新点"开始导入"，
        不存在"恢复"这个概念。

        只在真的有任务正在处理时才有意义——前端"暂停"按钮本来就只在这时候
        才会显示；空闲时调用是无操作，避免留下一个没有对应任务、永远不会
        被清掉的暂停标志。
        """
        with self._lock:
            if self._current_task is None:
                return
            self._pause_event.set()
            for task_id in list(self._queued_tasks.keys()):
                del self._queued_tasks[task_id]
                self._cancelled_ids.add(task_id)

    def book_has_pending_or_active_task(self, book_id: str) -> bool:
        with self._lock:
            if self._current_task is not None and self._current_task.book_id == book_id:
                return True
            return any(t.book_id == book_id for t in self._queued_tasks.values())

    def get_status(self) -> dict:
        with self._lock:
            pause_requested = self._pause_event.is_set()
            if self._current_task is not None:
                return {"busy": True, "reason": "ingesting",
                        "book_id": self._current_task.book_id,
                        "pause_requested": pause_requested}
            return {"busy": False, "reason": "idle", "book_id": None,
                    "pause_requested": pause_requested}

    def get_progress(self) -> dict:
        with self._lock:
            return {
                "progress": dict(self._progress) if self._progress is not None else None,
                "last_result": dict(self._last_result) if self._last_result is not None else None,
            }

    def _report_progress(self, update: dict) -> None:
        with self._lock:
            self._progress = update

    def wait_until_idle(self, timeout: float | None = None) -> None:
        # queue.Queue.join() 本身不接受 timeout 参数（任何 Python 版本都没有），
        # 这里复用它内部用来实现 join() 的同一个条件变量（all_tasks_done +
        # unfinished_tasks），自己包一层能超时的等待——测试如果真的卡死，
        # 会抛 TimeoutError 而不是永远挂起。
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._queue.all_tasks_done:
                if self._queue.unfinished_tasks == 0:
                    return
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError("wait_until_idle timed out")
            time.sleep(0.01)

    def _worker_loop(self) -> None:
        while True:
            task = self._queue.get()
            # 排队中的任务如果在这之前被 request_pause()（或手动"取消排队"）
            # 取消了，这里直接丢掉、不进 processor——不需要再等暂停标志清掉
            # 才能往下走，request_pause() 已经把它从 _queued_tasks 里摘掉了，
            # 这里只是把它从 self._queue 本身也清空。
            with self._lock:
                if task.task_id in self._cancelled_ids:
                    self._cancelled_ids.discard(task.task_id)
                    self._queue.task_done()
                    continue
                self._queued_tasks.pop(task.task_id, None)
                self._current_task = task
                self._progress = None
            try:
                summary = self._processor(task.book_id, task.file_paths,
                                          self._pause_event.is_set, self._report_progress)
            except Exception as e:
                # 兜底：处理器抛任何未捕获异常都不能杀死工作线程——否则 busy 永久
                # 卡死、删除拦截永久生效、后续任务全部滞留，只能重启应用。
                # 错误摘要进 last_result，前端轮询看到 error 键即知任务失败。
                print(f"[error] 导入任务处理器异常（task={task.task_id}, book={task.book_id}）: "
                      f"{type(e).__name__}: {e}")
                traceback.print_exc()
                summary = {"book_id": task.book_id, "error": f"{type(e).__name__}: {e}"}
            with self._lock:
                self._current_task = None
                self._progress = None
                if summary is not None:
                    # task_id 混进结果里，供前端做"这份结果是不是已经弹过
                    # 提示"的去重判断——不能拿结果内容本身去重：暂停发生在
                    # 文件还没开始处理之前时，重新提交同一批文件产生的结果
                    # 在内容上会一模一样（book_id/not_attempted 都相同），
                    # 内容去重会把第二次真实发生的结果误判成旧结果吞掉。
                    # task_id 每次 enqueue 都不同，没有这个问题。
                    self._last_result = {**summary, "task_id": task.task_id}
                # 暂停标志只服务于"让当前这个任务提前收尾"——任务一结束就
                # 无条件清掉，跟队列里还有没有别的任务无关：排队的任务在
                # request_pause() 那一刻已经被直接取消了，不存在"清了标志
                # 就会误放行下一个任务"这回事。
                self._pause_event.clear()
            self._queue.task_done()


_queue_singleton: Optional[ImportQueue] = None
_singleton_lock = threading.Lock()


def get_import_queue() -> ImportQueue:
    global _queue_singleton
    if _queue_singleton is None:
        with _singleton_lock:
            if _queue_singleton is None:
                from pipeline.api.ingest_runner import ingest_processor
                _queue_singleton = ImportQueue(processor=ingest_processor)
                _queue_singleton.start()
    return _queue_singleton


def reset_import_queue() -> None:
    """仅供测试用：清空单例，避免测试间互相污染。"""
    global _queue_singleton
    with _singleton_lock:
        _queue_singleton = None
