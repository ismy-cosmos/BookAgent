"""Tests for MarkerWorkerClient — subprocess.Popen is mocked; no real worker."""
import json
import queue
from unittest.mock import MagicMock, patch

import pytest

from pipeline.parse import Element
from pipeline.parse.marker import MarkerParsePaused
from pipeline.parse.marker_worker_client import (
    MarkerWorkerClient,
    _EOF_SENTINEL,
    _MARKER_WORKER_MAX_PAGES,
)
from pipeline.parse.parse_cache import _encode_element


def _reset():
    MarkerWorkerClient._proc = None
    MarkerWorkerClient._page_counter = 0
    MarkerWorkerClient._job_counter = 0
    MarkerWorkerClient._queue = None
    MarkerWorkerClient._stderr_lines.clear()
    MarkerWorkerClient._page_sep = None


def _make_element(page_num: int, content: str = "test") -> Element:
    return Element(type="text", content=content, page_num=page_num)


def _encoded(*elements: Element) -> list[dict]:
    return [_encode_element(e) for e in elements]


def _make_mock_proc():
    p = MagicMock()
    p.poll.return_value = None
    p.returncode = 0
    p.stdin = MagicMock()
    p.stdout = MagicMock()
    p.stderr = MagicMock()
    return p


def _setup_worker(mock_proc=None, page_counter=0, job_counter=0):
    if mock_proc is None:
        mock_proc = _make_mock_proc()
    MarkerWorkerClient._proc = mock_proc
    MarkerWorkerClient._queue = queue.Queue()
    MarkerWorkerClient._page_counter = page_counter
    MarkerWorkerClient._job_counter = job_counter


def _inject_ready():
    MarkerWorkerClient._queue.put(json.dumps({"ready": True, "page_sep": "@@BOOKAGENT_PAGE_BREAK@@"}))


def _inject_response(job: int, elements: list[Element], section_count: int = 1):
    MarkerWorkerClient._queue.put(json.dumps({
        "job": job, "ok": True,
        "elements": _encoded(*elements),
        "section_count": section_count,
    }))


def _inject_ok_false(job: int, error: str = "test error"):
    MarkerWorkerClient._queue.put(json.dumps({
        "job": job, "ok": False, "error": error,
    }))


def _inject_eof():
    MarkerWorkerClient._queue.put(_EOF_SENTINEL)


# ── Ready handshake ────────────────────────────────────────────────

def test_lazy_start_on_first_submit():
    _reset()
    mock_proc = _make_mock_proc()

    q = queue.Queue()
    q.put(json.dumps({"ready": True, "page_sep": "@@BP@@"}))
    q.put(json.dumps({"job": 1, "ok": True,
                      "elements": _encoded(_make_element(1)), "section_count": 1}))

    with patch("pipeline.parse.marker_worker_client.subprocess.Popen", return_value=mock_proc), \
         patch("pipeline.parse.marker_worker_client.queue.Queue", return_value=q):
        elements, sc = MarkerWorkerClient.submit("test.pdf", 1, should_pause=lambda: False)

    assert len(elements) == 1
    assert sc == 1
    assert mock_proc.stdin.write.called


def test_ready_handshake_worker_crash_during_startup():
    _reset()
    q = queue.Queue()
    q.put(_EOF_SENTINEL)

    with patch("pipeline.parse.marker_worker_client.subprocess.Popen"), \
         patch("pipeline.parse.marker_worker_client.queue.Queue", return_value=q):
        with pytest.raises(RuntimeError, match="crashed during startup"):
            MarkerWorkerClient.submit("test.pdf", 1, should_pause=lambda: False)


# ── Task round-trip ────────────────────────────────────────────────

def test_submit_round_trip():
    _reset()
    _setup_worker()
    _inject_ready()
    _inject_response(job=1, elements=[_make_element(1, "hello")])

    elements, sc = MarkerWorkerClient.submit("test.pdf", 1, should_pause=lambda: False)
    assert len(elements) == 1
    assert elements[0].content == "hello"
    assert sc == 1


def test_ok_false_raises_runtime_error():
    _reset()
    _setup_worker()
    _inject_ready()
    _inject_ok_false(job=1)

    with pytest.raises(RuntimeError, match="ok=false"):
        MarkerWorkerClient.submit("test.pdf", 1, should_pause=lambda: False)


# ── Page budget (pre-check) ────────────────────────────────────────

def test_page_budget_pre_check_recycles_before_exceeding():
    """counter=190 + batch=50 = 240 > 200 → recycle BEFORE processing"""
    _reset()
    mock_proc1 = _make_mock_proc()
    mock_proc2 = _make_mock_proc()

    # Worker 1 at 190 pages
    _setup_worker(mock_proc1, page_counter=190, job_counter=10)
    _inject_ready()

    # Submitting 50 pages → 190+50=240 > 200 → recycle before send.
    # After recycle, _ensure_worker spawns via Popen → mock_proc2.
    q2 = queue.Queue()
    q2.put(json.dumps({"ready": True, "page_sep": "@@BP@@"}))
    q2.put(json.dumps({"job": 1, "ok": True,
                       "elements": _encoded(*([_make_element(1)] * 50)),
                       "section_count": 50}))

    with patch("pipeline.parse.marker_worker_client.subprocess.Popen", return_value=mock_proc2), \
         patch("pipeline.parse.marker_worker_client.queue.Queue", return_value=q2):
        elements, sc = MarkerWorkerClient.submit("batch.pdf", 50, should_pause=lambda: False)

    assert len(elements) == 50
    assert sc == 50
    # After processing: counter = 0 (reset by _ensure_worker) + 50 = 50
    assert MarkerWorkerClient._page_counter == 50
    # Verify shutdown was sent to mock_proc1
    written = "".join(c[0][0] for c in mock_proc1.stdin.write.call_args_list)
    assert '"cmd": "shutdown"' in written


# ── Crash retry ────────────────────────────────────────────────────

def test_worker_death_mid_task_retries_once():
    """Worker 1 (pre-set) dies → retry spawns new worker via Popen."""
    _reset()
    mock_proc1 = _make_mock_proc()
    mock_proc_new = _make_mock_proc()

    with patch("pipeline.parse.marker_worker_client.subprocess.Popen",
               return_value=mock_proc_new) as mock_popen:
        # Worker 1 pre-set, sends ready, then dies before responding
        _setup_worker(mock_proc1, page_counter=0, job_counter=0)
        _inject_ready()
        _inject_eof()

        # Retry: _ensure_worker spawns → mock_proc_new
        q2 = queue.Queue()
        q2.put(json.dumps({"ready": True, "page_sep": "@@BP@@"}))
        q2.put(json.dumps({"job": 1, "ok": True,
                           "elements": _encoded(_make_element(1)), "section_count": 1}))

        with patch("pipeline.parse.marker_worker_client.queue.Queue", return_value=q2):
            elements, sc = MarkerWorkerClient.submit("test.pdf", 1, should_pause=lambda: False)

    assert len(elements) == 1
    assert sc == 1
    mock_popen.assert_called_once()  # retry spawned a new worker


def test_double_crash_raises_runtime_error():
    """First crash → retry spawn → second crash → RuntimeError."""
    _reset()
    mock_proc1 = _make_mock_proc()
    mock_proc_retry = _make_mock_proc()

    with patch("pipeline.parse.marker_worker_client.subprocess.Popen",
               return_value=mock_proc_retry) as mock_popen:
        # Worker 1 dies
        _setup_worker(mock_proc1, page_counter=0, job_counter=0)
        _inject_ready()
        _inject_eof()

        # Retry spawns, also dies
        q2 = queue.Queue()
        q2.put(json.dumps({"ready": True, "page_sep": "@@BP@@"}))
        q2.put(_EOF_SENTINEL)

        with patch("pipeline.parse.marker_worker_client.queue.Queue", return_value=q2):
            with pytest.raises(RuntimeError, match="crashed twice"):
                MarkerWorkerClient.submit("test.pdf", 1, should_pause=lambda: False)

    mock_popen.assert_called_once()  # one retry spawn, then gave up


# ── Pause ──────────────────────────────────────────────────────────

def test_pause_during_processing_kills_worker():
    _reset()
    mock_proc = _make_mock_proc()
    _setup_worker(mock_proc)
    _inject_ready()

    with pytest.raises(MarkerParsePaused):
        MarkerWorkerClient.submit("test.pdf", 1, should_pause=lambda: True)

    mock_proc.kill.assert_called_once()


# ── shutdown() ─────────────────────────────────────────────────────

def test_shutdown_idempotent_when_no_worker():
    _reset()
    MarkerWorkerClient.shutdown()


def test_shutdown_sends_command_and_waits():
    _reset()
    mock_proc = _make_mock_proc()
    _setup_worker(mock_proc)
    _inject_ready()
    _inject_response(job=1, elements=[_make_element(1)])
    MarkerWorkerClient.submit("test.pdf", 1, should_pause=lambda: False)

    MarkerWorkerClient.shutdown()
    written = "".join(c[0][0] for c in mock_proc.stdin.write.call_args_list)
    assert '"cmd": "shutdown"' in written


def test_shutdown_then_lazy_restart():
    _reset()
    mock_proc1 = _make_mock_proc()
    mock_proc2 = _make_mock_proc()

    # First submit
    q1 = queue.Queue()
    q1.put(json.dumps({"ready": True, "page_sep": "@@BP@@"}))
    q1.put(json.dumps({"job": 1, "ok": True,
                       "elements": _encoded(_make_element(1)), "section_count": 1}))
    with patch("pipeline.parse.marker_worker_client.subprocess.Popen", return_value=mock_proc1), \
         patch("pipeline.parse.marker_worker_client.queue.Queue", return_value=q1):
        MarkerWorkerClient.submit("test1.pdf", 1, should_pause=lambda: False)

    MarkerWorkerClient.shutdown()
    assert MarkerWorkerClient._proc is None

    # Second submit spawns new worker
    q2 = queue.Queue()
    q2.put(json.dumps({"ready": True, "page_sep": "@@BP@@"}))
    q2.put(json.dumps({"job": 1, "ok": True,
                       "elements": _encoded(_make_element(1)), "section_count": 1}))
    with patch("pipeline.parse.marker_worker_client.subprocess.Popen", return_value=mock_proc2), \
         patch("pipeline.parse.marker_worker_client.queue.Queue", return_value=q2):
        _, _ = MarkerWorkerClient.submit("test2.pdf", 1, should_pause=lambda: False)
    assert MarkerWorkerClient._proc is mock_proc2
