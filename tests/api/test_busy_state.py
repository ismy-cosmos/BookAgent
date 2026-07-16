import threading

from pipeline.api import busy_state


def teardown_function():
    # 每个测试后强制清空，避免一个测试忘了 release() 拖累下一个测试。
    busy_state.release()


def test_try_acquire_succeeds_when_idle():
    conflict = busy_state.try_acquire("ingesting", "ostep")
    assert conflict is None
    assert busy_state.get_state() == busy_state.BusyState(reason="ingesting", book_id="ostep")


def test_try_acquire_returns_conflict_when_already_held():
    busy_state.try_acquire("ingesting", "ostep")
    conflict = busy_state.try_acquire("answering", "other-book")
    assert conflict == busy_state.BusyState(reason="ingesting", book_id="ostep")
    # 第二次获取失败，状态还是第一次那个持有者的，不会被覆盖
    assert busy_state.get_state() == busy_state.BusyState(reason="ingesting", book_id="ostep")


def test_release_clears_state():
    busy_state.try_acquire("answering", "ostep")
    busy_state.release()
    assert busy_state.get_state() is None


def test_release_when_idle_is_a_no_op():
    busy_state.release()  # 不应该抛异常
    assert busy_state.get_state() is None


def test_get_state_returns_none_when_idle():
    assert busy_state.get_state() is None


def test_concurrent_try_acquire_only_one_succeeds():
    successes = []
    lock = threading.Lock()

    def worker(i):
        conflict = busy_state.try_acquire("answering", f"book-{i}")
        if conflict is None:
            with lock:
                successes.append(i)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) == 1
