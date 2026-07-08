from __future__ import annotations
import queue
import threading
import uuid
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ImportTask:
    task_id: str
    book_id: str
    file_paths: list[str]


ProcessorFn = Callable[[str, list[str], Callable[[], bool]], None]


class ImportQueue:
    def __init__(self, processor: ProcessorFn) -> None:
        self._processor = processor
        self._queue: "queue.Queue[ImportTask]" = queue.Queue()
        self._lock = threading.Lock()
        self._current_task: Optional[ImportTask] = None
        self._queued_tasks: dict[str, ImportTask] = {}
        self._cancelled_ids: set[str] = set()
        self._paused_tasks: dict[str, ImportTask] = {}
        self._pause_event = threading.Event()
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

    def request_pause(self, task_id: str) -> bool:
        with self._lock:
            if self._current_task is not None and self._current_task.task_id == task_id:
                self._pause_event.set()
                return True
            return False

    def resume(self, task_id: str) -> bool:
        with self._lock:
            task = self._paused_tasks.pop(task_id, None)
            if task is None:
                return False
            self._queued_tasks[task.task_id] = task
        self._queue.put(task)
        return True

    def book_has_pending_or_active_task(self, book_id: str) -> bool:
        with self._lock:
            if self._current_task is not None and self._current_task.book_id == book_id:
                return True
            return any(t.book_id == book_id for t in self._queued_tasks.values())

    def get_status(self) -> dict:
        with self._lock:
            if self._current_task is not None:
                return {"busy": True, "reason": "ingesting", "book_id": self._current_task.book_id}
        return {"busy": False, "reason": "idle", "book_id": None}

    def wait_until_idle(self, timeout: float | None = None) -> None:
        # queue.Queue.join() 本身不接受 timeout 参数（任何 Python 版本都没有），
        # 这里复用它内部用来实现 join() 的同一个条件变量（all_tasks_done +
        # unfinished_tasks），自己包一层能超时的等待——测试如果真的卡死，
        # 会抛 TimeoutError 而不是永远挂起。
        import time
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
            with self._lock:
                if task.task_id in self._cancelled_ids:
                    self._cancelled_ids.discard(task.task_id)
                    self._queue.task_done()
                    continue
                self._queued_tasks.pop(task.task_id, None)
                self._current_task = task
                self._pause_event.clear()
            self._processor(task.book_id, task.file_paths, self._pause_event.is_set)
            with self._lock:
                if self._pause_event.is_set():
                    self._paused_tasks[task.task_id] = task
                self._current_task = None
            self._queue.task_done()


def _placeholder_processor(book_id: str, file_paths: list[str], should_pause) -> None:
    """占位实现：真正的解析/VLM/向量化/写库逻辑属于 issue #27，这里先什么都不做，
    只是让 ImportQueue 在生产环境里能被实例化、跑通队列本身的逻辑。"""


_queue_singleton: Optional[ImportQueue] = None


def get_import_queue() -> ImportQueue:
    global _queue_singleton
    if _queue_singleton is None:
        _queue_singleton = ImportQueue(processor=_placeholder_processor)
        _queue_singleton.start()
    return _queue_singleton
