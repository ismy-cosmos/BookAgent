import threading
import time

from pipeline.api.import_queue import ImportQueue


class _RecordingProcessor:
    """记录每次被调用时收到的 book_id/file_paths，直接处理完不模拟耗时。"""

    def __init__(self):
        self.calls: list[tuple[str, list[str]]] = []

    def __call__(self, book_id: str, file_paths: list[str], should_pause,
                 report_progress) -> None:
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
    assert q.get_status() == {
        "busy": False, "reason": "idle", "book_id": None, "pause_requested": False,
    }


def test_get_status_busy_while_processing():
    started = threading.Event()
    release = threading.Event()

    def slow_processor(book_id, file_paths, should_pause, report_progress):
        started.set()
        release.wait(timeout=2.0)

    q = ImportQueue(processor=slow_processor)
    q.start()
    q.enqueue("ostep", ["ch1.pdf"])

    assert started.wait(timeout=2.0)
    assert q.get_status() == {
        "busy": True, "reason": "ingesting", "book_id": "ostep", "pause_requested": False,
    }

    release.set()
    q.wait_until_idle(timeout=2.0)
    assert q.get_status() == {
        "busy": False, "reason": "idle", "book_id": None, "pause_requested": False,
    }


def test_cancel_queued_task_succeeds_and_it_never_runs():
    processor = _RecordingProcessor()
    blocker_started = threading.Event()
    blocker_release = threading.Event()

    def blocking_first_call(book_id, file_paths, should_pause, report_progress):
        if not blocker_started.is_set():
            blocker_started.set()
            blocker_release.wait(timeout=2.0)
        else:
            processor(book_id, file_paths, should_pause, report_progress)

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

    def slow_processor(book_id, file_paths, should_pause, report_progress):
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


# ── 按工作线程暂停 ───────────────────────────────────────────────────────

def test_should_pause_reflects_request_pause():
    """处理器拿到的 should_pause 就是工作线程级暂停标志——请求暂停后立刻变 True。"""
    observed = []
    started = threading.Event()
    release = threading.Event()

    def observing_processor(book_id, file_paths, should_pause, report_progress):
        started.set()
        release.wait(timeout=2.0)
        observed.append(should_pause())

    q = ImportQueue(processor=observing_processor)
    q.start()
    q.enqueue("ostep", ["f1.pdf"])

    assert started.wait(timeout=2.0)
    q.request_pause()
    release.set()
    q.wait_until_idle(timeout=2.0)

    assert observed == [True]


def test_pause_stops_worker_from_taking_next_queued_task():
    processed = []
    started = threading.Event()
    release = threading.Event()

    def slow_first_processor(book_id, file_paths, should_pause, report_progress):
        processed.append(book_id)
        if len(processed) == 1:
            started.set()
            release.wait(timeout=2.0)

    q = ImportQueue(processor=slow_first_processor)
    q.start()
    q.enqueue("book-a", ["a1.pdf"])
    q.enqueue("book-b", ["b1.pdf"])  # 排队等着

    assert started.wait(timeout=2.0)
    q.request_pause()  # 第一个任务还在跑的时候请求暂停
    release.set()      # 放行第一个任务收尾

    time.sleep(0.3)    # 给"如果它会继续取任务"留出反应时间
    assert processed == ["book-a"]  # book-b 没有被开始处理

    q.resume()
    q.wait_until_idle(timeout=2.0)
    assert processed == ["book-a", "book-b"]  # 恢复后才轮到 book-b


def test_pause_while_idle_holds_subsequently_enqueued_task():
    processor = _RecordingProcessor()
    q = ImportQueue(processor=processor)
    q.start()

    q.request_pause()  # 空闲时请求暂停
    q.enqueue("ostep", ["f1.pdf"])

    time.sleep(0.3)
    assert processor.calls == []  # 已暂停：新入队的任务不会被开始处理

    q.resume()
    q.wait_until_idle(timeout=2.0)
    assert processor.calls == [("ostep", ["f1.pdf"])]


def test_cancel_works_on_task_held_during_pause():
    processor = _RecordingProcessor()
    q = ImportQueue(processor=processor)
    q.start()

    q.request_pause()
    task_id = q.enqueue("ostep", ["f1.pdf"])
    time.sleep(0.2)  # 让工作线程有机会把任务从队列里取出来、进入暂停等待

    assert q.cancel(task_id) is True  # 暂停期间任务仍算"排队中"，可以取消

    q.resume()
    q.wait_until_idle(timeout=2.0)
    assert processor.calls == []  # 被取消的任务恢复后也不会被处理


def test_get_status_pausing_vs_paused():
    """pause_requested=True + busy=True 是"正在暂停中"；+ busy=False 是"已暂停"。"""
    started = threading.Event()
    release = threading.Event()

    def slow_processor(book_id, file_paths, should_pause, report_progress):
        started.set()
        release.wait(timeout=2.0)

    q = ImportQueue(processor=slow_processor)
    q.start()
    q.enqueue("ostep", ["f1.pdf"])
    assert started.wait(timeout=2.0)

    q.request_pause()
    status = q.get_status()
    assert status["busy"] is True and status["pause_requested"] is True  # 正在暂停中

    release.set()
    q.wait_until_idle(timeout=2.0)
    status = q.get_status()
    assert status["busy"] is False and status["pause_requested"] is True  # 已暂停

    q.resume()
    assert q.get_status()["pause_requested"] is False


def test_book_has_pending_or_active_task_true_for_task_held_during_pause():
    """暂停期间被扣住的任务仍算"排队中"——它的书必须继续被删除拦截保护。"""
    q = ImportQueue(processor=_RecordingProcessor())
    q.start()

    q.request_pause()
    q.enqueue("ostep", ["f1.pdf"])
    time.sleep(0.2)

    assert q.book_has_pending_or_active_task("ostep") is True

    q.resume()
    q.wait_until_idle(timeout=2.0)
    assert q.book_has_pending_or_active_task("ostep") is False


# ── 进度与结果存档 ───────────────────────────────────────────────────────

def test_progress_visible_while_processing_and_cleared_after():
    reported = threading.Event()
    release = threading.Event()

    def reporting_processor(book_id, file_paths, should_pause, report_progress):
        report_progress({"stage": "parsing", "current_file": 1, "total_files": 2,
                         "current_image": None, "total_images": None})
        reported.set()
        release.wait(timeout=2.0)

    q = ImportQueue(processor=reporting_processor)
    q.start()
    q.enqueue("ostep", ["f1.pdf", "f2.pdf"])

    assert reported.wait(timeout=2.0)
    progress = q.get_progress()["progress"]
    assert progress == {"stage": "parsing", "current_file": 1, "total_files": 2,
                        "current_image": None, "total_images": None}

    release.set()
    q.wait_until_idle(timeout=2.0)
    assert q.get_progress()["progress"] is None  # 任务结束，进度清空


def test_last_result_stored_from_processor_return_value():
    summary = {"book_id": "ostep", "total_chunks": 5, "failures": [],
               "not_attempted": [], "aborted_early": False}

    def returning_processor(book_id, file_paths, should_pause, report_progress):
        return summary

    q = ImportQueue(processor=returning_processor)
    q.start()
    q.enqueue("ostep", ["f1.pdf"])
    q.wait_until_idle(timeout=2.0)

    assert q.get_progress()["last_result"] == summary


def test_last_result_none_before_any_task():
    q = ImportQueue(processor=_RecordingProcessor())
    q.start()
    assert q.get_progress() == {"progress": None, "last_result": None}


def test_processor_returning_none_keeps_previous_last_result():
    results = [{"book_id": "a", "total_chunks": 1, "failures": [],
                "not_attempted": [], "aborted_early": False}, None]

    def sequenced_processor(book_id, file_paths, should_pause, report_progress):
        return results.pop(0)

    q = ImportQueue(processor=sequenced_processor)
    q.start()
    q.enqueue("book-a", ["a1.pdf"])
    q.wait_until_idle(timeout=2.0)
    first = q.get_progress()["last_result"]

    q.enqueue("book-b", ["b1.pdf"])
    q.wait_until_idle(timeout=2.0)

    assert q.get_progress()["last_result"] == first  # None 返回值不覆盖已有存档


# ── 删除拦截（语义不变，签名适配）───────────────────────────────────────

def test_book_has_pending_or_active_task_true_while_queued():
    started = threading.Event()
    release = threading.Event()

    def slow_processor(book_id, file_paths, should_pause, report_progress):
        started.set()
        release.wait(timeout=2.0)

    q = ImportQueue(processor=slow_processor)
    q.start()
    q.enqueue("book-a", ["a1.pdf"])  # 占住工作线程
    assert started.wait(timeout=2.0)

    q.enqueue("book-b", ["b1.pdf"])  # 排队中
    assert q.book_has_pending_or_active_task("book-b") is True

    release.set()
    q.wait_until_idle(timeout=2.0)


def test_book_has_pending_or_active_task_true_while_processing():
    started = threading.Event()
    release = threading.Event()

    def slow_processor(book_id, file_paths, should_pause, report_progress):
        started.set()
        release.wait(timeout=2.0)

    q = ImportQueue(processor=slow_processor)
    q.start()
    q.enqueue("ostep", ["ch1.pdf"])
    assert started.wait(timeout=2.0)

    assert q.book_has_pending_or_active_task("ostep") is True

    release.set()
    q.wait_until_idle(timeout=2.0)


def test_book_has_pending_or_active_task_false_after_cancel():
    processor = _RecordingProcessor()
    blocker_started = threading.Event()
    blocker_release = threading.Event()

    def blocking_first_call(book_id, file_paths, should_pause, report_progress):
        if not blocker_started.is_set():
            blocker_started.set()
            blocker_release.wait(timeout=2.0)

    q = ImportQueue(processor=blocking_first_call)
    q.start()
    q.enqueue("book-a", ["a1.pdf"])
    assert blocker_started.wait(timeout=2.0)

    task_id_b = q.enqueue("book-b", ["b1.pdf"])
    assert q.cancel(task_id_b) is True
    assert q.book_has_pending_or_active_task("book-b") is False

    blocker_release.set()
    q.wait_until_idle(timeout=2.0)


def test_book_has_pending_or_active_task_false_after_completed():
    q = ImportQueue(processor=_RecordingProcessor())
    q.start()
    q.enqueue("ostep", ["ch1.pdf"])
    q.wait_until_idle(timeout=2.0)
    assert q.book_has_pending_or_active_task("ostep") is False


def test_book_has_pending_or_active_task_false_for_unrelated_book():
    started = threading.Event()
    release = threading.Event()

    def slow_processor(book_id, file_paths, should_pause, report_progress):
        started.set()
        release.wait(timeout=2.0)

    q = ImportQueue(processor=slow_processor)
    q.start()
    q.enqueue("book-a", ["a1.pdf"])
    assert started.wait(timeout=2.0)

    assert q.book_has_pending_or_active_task("book-unrelated") is False

    release.set()
    q.wait_until_idle(timeout=2.0)
