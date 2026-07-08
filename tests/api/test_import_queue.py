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


def test_cancel_queued_task_succeeds_and_it_never_runs():
    processor = _RecordingProcessor()
    blocker_started = threading.Event()
    blocker_release = threading.Event()

    def blocking_first_call(book_id, file_paths, should_pause):
        if not blocker_started.is_set():
            blocker_started.set()
            blocker_release.wait(timeout=2.0)
        else:
            processor(book_id, file_paths, should_pause)

    q = ImportQueue(processor=blocking_first_call)
    q.start()

    q.enqueue("book-a", ["a1.pdf"])  # 占住工作线程，让第二个任务保持"排队中"
    assert blocker_started.wait(timeout=2.0)

    task_id_b = q.enqueue("book-b", ["b1.pdf"])
    assert q.cancel(task_id_b) is True

    blocker_release.set()
    q.wait_until_idle(timeout=2.0)

    assert processor.calls == []  # book-b 的任务从没被真正处理过


def test_cancel_already_processing_task_fails():
    started = threading.Event()
    release = threading.Event()

    def slow_processor(book_id, file_paths, should_pause):
        started.set()
        release.wait(timeout=2.0)

    q = ImportQueue(processor=slow_processor)
    q.start()
    task_id = q.enqueue("ostep", ["ch1.pdf"])

    assert started.wait(timeout=2.0)
    assert q.cancel(task_id) is False  # 已经在处理中，取消失败

    release.set()
    q.wait_until_idle(timeout=2.0)


def test_cancel_unknown_task_id_fails():
    q = ImportQueue(processor=_RecordingProcessor())
    q.start()
    assert q.cancel("does-not-exist") is False


def test_pause_takes_effect_at_file_boundary_not_mid_file():
    """处理器模拟处理两个文件；请求暂停后，当前文件必须先跑完，才会真正停下来。"""
    completed_files: list[str] = []
    release_file_1 = threading.Event()
    file_1_started = threading.Event()

    def two_file_processor(book_id, file_paths, should_pause):
        for f in file_paths:
            if f == "f1.pdf":
                file_1_started.set()
                release_file_1.wait(timeout=2.0)
            completed_files.append(f)
            if should_pause():
                return

    q = ImportQueue(processor=two_file_processor)
    q.start()
    task_id = q.enqueue("ostep", ["f1.pdf", "f2.pdf"])

    assert file_1_started.wait(timeout=2.0)
    assert q.request_pause(task_id) is True

    # 暂停请求发出后，f1 还没处理完，忙碌状态必须依然是 True
    assert q.get_status()["busy"] is True

    release_file_1.set()  # 放行，让 f1 跑完
    q.wait_until_idle(timeout=2.0)

    assert completed_files == ["f1.pdf"]  # f2 没有被处理——暂停在文件边界生效
    assert q.get_status() == {"busy": False, "reason": "idle", "book_id": None}


def test_paused_task_does_not_auto_resume():
    """入队后不能立刻调用 request_pause——工作线程有没有真的开始处理这个任务
    完全没保证，必须先等它明确进入处理中，暂停请求才有意义可以断言成功。"""
    file_1_started = threading.Event()
    release_file_1 = threading.Event()

    def two_file_processor(book_id, file_paths, should_pause):
        for f in file_paths:
            if f == "f1.pdf":
                file_1_started.set()
                release_file_1.wait(timeout=2.0)
            if should_pause():
                return

    q = ImportQueue(processor=two_file_processor)
    q.start()
    task_id = q.enqueue("ostep", ["f1.pdf", "f2.pdf"])

    assert file_1_started.wait(timeout=2.0)
    assert q.request_pause(task_id) is True  # 确认暂停请求真的被工作线程接受了

    release_file_1.set()
    q.wait_until_idle(timeout=2.0)
    assert q.get_status() == {"busy": False, "reason": "idle", "book_id": None}

    time.sleep(0.05)  # 给"如果它会自动恢复"留出反应时间
    assert q.get_status() == {"busy": False, "reason": "idle", "book_id": None}


def test_resume_fails_for_a_task_that_was_never_paused():
    processor = _RecordingProcessor()

    q = ImportQueue(processor=processor)
    q.start()
    task_id = q.enqueue("ostep", ["f1.pdf"])
    q.wait_until_idle(timeout=2.0)  # 直接跑完，从没暂停过

    assert q.resume(task_id) is False  # 没暂停过的任务不能恢复


def test_resume_after_pause_reenqueues_same_task():
    """同样不能入队后立刻暂停——用跟 test_pause_takes_effect_at_file_boundary_not_mid_file
    一样的阻塞同步方式，确保暂停请求是在工作线程真正处理到 f1 的时候打进去的。"""
    call_log: list[str] = []
    file_1_started = threading.Event()
    release_file_1 = threading.Event()

    def one_shot_pause_processor(book_id, file_paths, should_pause):
        for f in file_paths:
            if f == "f1.pdf":
                file_1_started.set()
                release_file_1.wait(timeout=2.0)
            call_log.append(f)
            if should_pause():
                return

    q = ImportQueue(processor=one_shot_pause_processor)
    q.start()
    task_id = q.enqueue("ostep", ["f1.pdf", "f2.pdf"])

    assert file_1_started.wait(timeout=2.0)
    assert q.request_pause(task_id) is True
    release_file_1.set()

    q.wait_until_idle(timeout=2.0)
    assert call_log == ["f1.pdf"]

    assert q.resume(task_id) is True
    q.wait_until_idle(timeout=2.0)

    # 恢复后重新丢回队列，重新从头跑（跳过已完成文件是 issue #27 里
    # ingest.py 的 sha 去重逻辑负责的，不是 ImportQueue 自己的职责）
    assert call_log == ["f1.pdf", "f1.pdf", "f2.pdf"]


def test_request_pause_unknown_or_not_processing_task_fails():
    q = ImportQueue(processor=_RecordingProcessor())
    q.start()
    assert q.request_pause("does-not-exist") is False

    task_id = q.enqueue("ostep", ["f1.pdf"])
    q.wait_until_idle(timeout=2.0)
    assert q.request_pause(task_id) is False  # 已经处理完了，不是"处理中"
