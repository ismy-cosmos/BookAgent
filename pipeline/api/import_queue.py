from __future__ import annotations
import queue
import threading
import time
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

_PAUSE_POLL_INTERVAL_S = 0.05


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
        """按工作线程暂停：当前任务在文件/图片边界提前收尾（run_ingest 里的
        should_pause 检查点），之后不再开始处理任何任务，直到 resume()。"""
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()

    def book_has_pending_or_active_task(self, book_id: str) -> bool:
        with self._lock:
            if self._current_task is not None and self._current_task.book_id == book_id:
                return True
            return any(t.book_id == book_id for t in self._queued_tasks.values())

    def get_status(self) -> dict:
        with self._lock:
            if self._current_task is not None:
                return {"busy": True, "reason": "ingesting",
                        "book_id": self._current_task.book_id,
                        "pause_requested": self._pause_event.is_set()}
        return {"busy": False, "reason": "idle", "book_id": None,
                "pause_requested": self._pause_event.is_set()}

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
            # 取到任务后先确认暂停状态——暂停可能是上一个任务收尾时请求的，
            # 也可能是空闲期间请求的。等待期间任务仍留在 _queued_tasks 里
            # （算"排队中"：删除拦截继续生效、cancel 依然可用）。
            while self._pause_event.is_set():
                time.sleep(_PAUSE_POLL_INTERVAL_S)
            with self._lock:
                if task.task_id in self._cancelled_ids:
                    self._cancelled_ids.discard(task.task_id)
                    self._queue.task_done()
                    continue
                self._queued_tasks.pop(task.task_id, None)
                self._current_task = task
                self._progress = None
            summary = self._processor(task.book_id, task.file_paths,
                                      self._pause_event.is_set, self._report_progress)
            with self._lock:
                self._current_task = None
                self._progress = None
                if summary is not None:
                    self._last_result = summary
            self._queue.task_done()


_queue_singleton: Optional[ImportQueue] = None


def get_import_queue() -> ImportQueue:
    global _queue_singleton
    if _queue_singleton is None:
        from pipeline.api.ingest_runner import ingest_processor
        _queue_singleton = ImportQueue(processor=ingest_processor)
        _queue_singleton.start()
    return _queue_singleton
