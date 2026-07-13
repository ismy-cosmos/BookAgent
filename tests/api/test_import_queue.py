import threading
import time

import pipeline.api.import_queue as iq_module
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


def test_get_import_queue_concurrent_first_access_constructs_only_once():
    iq_module.reset_import_queue()
    barrier = threading.Barrier(20)
    results: list[iq_module.ImportQueue] = []
    results_lock = threading.Lock()

    def worker():
        barrier.wait()
        q = iq_module.get_import_queue()
        with results_lock:
            results.append(q)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len({id(r) for r in results}) == 1
    iq_module.reset_import_queue()


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


def test_get_status_pausing_while_task_still_running():
    """pause_requested=True + busy=True 是"正在暂停中"。"""
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


def test_pause_flag_auto_clears_once_queue_is_empty_after_task_ends():
    """方案B：暂停标志的意义是"接下来还要不要继续处理"——队列空了（没有
    下一个任务会被它拦住）就没有继续留着的意义，任务一收尾就自动清掉。

    覆盖"try"那种真实场景：批次里文件/图片太少，暂停请求根本没赶上任何
    一次边界检查（这里用一个完全不理会 should_pause、跑到底才返回的
    processor 模拟"没被真正打断"），任务正常跑完，但标志之前会一直留着
    true 不被清除，导致明明没有任何东西要恢复，前端却会一直显示"已暂停"。
    """
    started = threading.Event()
    release = threading.Event()

    def ignores_pause_processor(book_id, file_paths, should_pause, report_progress):
        started.set()
        release.wait(timeout=2.0)  # 模拟"正在处理中"，不检查 should_pause

    q = ImportQueue(processor=ignores_pause_processor)
    q.start()
    q.enqueue("ostep", ["f1.pdf"])
    assert started.wait(timeout=2.0)

    q.request_pause()  # 处理过程中请求暂停，但这个 processor 完全不理会它
    release.set()      # 放行，任务正常跑完（模拟单文件/单图批次里没有
                        # 任何边界检查能捕捉到这次暂停请求）
    q.wait_until_idle(timeout=2.0)

    assert q.get_status()["pause_requested"] is False  # 队列空了，自动清掉


def test_pause_flag_not_cleared_while_another_task_still_queued():
    """队列里还排着别的任务时，暂停标志不能被清掉——不然"暂停中不取下一个
    任务"这个既有保护就失效了。"""
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
    q.enqueue("book-b", ["b1.pdf"])  # 排队等着，book-a 收尾时队列不是空的

    assert started.wait(timeout=2.0)
    q.request_pause()
    release.set()
    time.sleep(0.3)  # 给"如果标志被清掉、book-b 会被开始处理"留出反应时间

    assert processed == ["book-a"]  # book-b 依然没有被开始处理
    assert q.get_status()["pause_requested"] is True  # 标志还在，没被清

    q.resume()
    q.wait_until_idle(timeout=2.0)
    assert processed == ["book-a", "book-b"]


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


def test_worker_survives_processor_exception():
    """处理器抛未捕获异常不能杀死工作线程——线程要活着继续服务后续任务，
    状态不能卡在 busy。"""
    calls = []

    def flaky_processor(book_id, file_paths, should_pause, report_progress):
        calls.append(book_id)
        if book_id == "bad-book":
            raise RuntimeError("boom")
        return {"book_id": book_id, "total_chunks": 1, "failures": [],
                "not_attempted": [], "aborted_early": False}

    q = ImportQueue(processor=flaky_processor)
    q.start()
    q.enqueue("bad-book", ["a.pdf"])
    q.enqueue("good-book", ["b.pdf"])
    q.wait_until_idle(timeout=2.0)

    assert calls == ["bad-book", "good-book"]  # 第二个任务照常被处理
    assert q.get_status()["busy"] is False     # 状态没有卡死
    assert q.get_progress()["last_result"]["book_id"] == "good-book"  # 后续任务正常存档


def test_processor_exception_recorded_in_last_result():
    def exploding_processor(book_id, file_paths, should_pause, report_progress):
        raise RuntimeError("manifest 损坏")

    q = ImportQueue(processor=exploding_processor)
    q.start()
    q.enqueue("ostep", ["a.pdf"])
    q.wait_until_idle(timeout=2.0)

    last = q.get_progress()["last_result"]
    assert last["book_id"] == "ostep"
    assert "RuntimeError" in last["error"] and "manifest 损坏" in last["error"]


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
