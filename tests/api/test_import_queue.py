import threading
import time

from pipeline.api.import_queue import ImportQueue


class _RecordingProcessor:
    """记录每次被调用时收到的 book_id/file_paths，直接处理完不模拟耗时。"""

    def __init__(self):
        self.calls: list[tuple[str, list[str]]] = []

    def __call__(self, book_id: str, file_paths: list[str], should_pause) -> None:
        self.calls.append((book_id, file_paths))


def test_enqueue_returns_task_id():
    q = ImportQueue(processor=_RecordingProcessor())
    q.start()
    task_id = q.enqueue("ostep", ["ch1.pdf"])
    assert isinstance(task_id, str)
    assert len(task_id) > 0


def test_tasks_processed_in_fifo_order():
    processor = _RecordingProcessor()
    q = ImportQueue(processor=processor)
    q.start()

    q.enqueue("book-a", ["a1.pdf"])
    q.enqueue("book-b", ["b1.pdf"])
    q.enqueue("book-a", ["a2.pdf"])

    q.wait_until_idle(timeout=2.0)

    assert processor.calls == [
        ("book-a", ["a1.pdf"]),
        ("book-b", ["b1.pdf"]),
        ("book-a", ["a2.pdf"]),
    ]


def test_no_cross_book_leakage():
    """连续处理不同书的任务时，处理器每次收到的 book_id 必须精确对应它自己的任务，不能串。"""
    processor = _RecordingProcessor()
    q = ImportQueue(processor=processor)
    q.start()

    for i in range(10):
        book_id = f"book-{i % 3}"
        q.enqueue(book_id, [f"{book_id}-file{i}.pdf"])

    q.wait_until_idle(timeout=2.0)

    assert len(processor.calls) == 10
    for book_id, file_paths in processor.calls:
        assert file_paths[0].startswith(book_id)


def test_get_status_idle_before_anything_enqueued():
    q = ImportQueue(processor=_RecordingProcessor())
    q.start()
    assert q.get_status() == {"busy": False, "reason": "idle", "book_id": None}


def test_get_status_busy_while_processing():
    started = threading.Event()
    release = threading.Event()

    def slow_processor(book_id, file_paths, should_pause):
        started.set()
        release.wait(timeout=2.0)

    q = ImportQueue(processor=slow_processor)
    q.start()
    q.enqueue("ostep", ["ch1.pdf"])

    assert started.wait(timeout=2.0)
    assert q.get_status() == {"busy": True, "reason": "ingesting", "book_id": "ostep"}

    release.set()
    q.wait_until_idle(timeout=2.0)
    assert q.get_status() == {"busy": False, "reason": "idle", "book_id": None}
