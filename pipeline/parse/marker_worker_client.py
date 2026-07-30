"""Parent-process client for the marker worker subprocess.

Module-level singleton — ImportQueue uses a single worker thread so no
concurrent submit() calls occur.
"""
from __future__ import annotations
import collections
import json
import os
import queue
import subprocess
import sys
import threading
from typing import Callable

from pipeline.parse.marker import MarkerParsePaused
from pipeline.parse.parse_cache import _decode_element

_MARKER_WORKER_MAX_PAGES = int(os.environ.get("MARKER_WORKER_MAX_PAGES", "200"))
_SHUTDOWN_TIMEOUT_S = 10.0
_EOF_SENTINEL = object()


class MarkerWorkerClient:
    """Singleton client that manages a long-lived marker worker subprocess."""

    _proc: subprocess.Popen | None = None
    _page_counter: int = 0
    _job_counter: int = 0
    _queue: queue.Queue | None = None
    _stderr_lines: collections.deque = collections.deque(maxlen=50)
    _page_sep: str | None = None

    # ── public API ──────────────────────────────────────────────────

    @classmethod
    def submit(
        cls,
        pdf_path: str,
        expected_pages: int,
        should_pause: Callable[[], bool],
    ) -> tuple[list, int]:
        """Send a single-batch PDF to the worker, return (elements, section_count).

        Page budget is checked BEFORE sending the job — the worker never
        accumulates more than MARKER_WORKER_MAX_PAGES.  Crash retry (once),
        pause detection.  ok:false responses recycle the worker (the job
        consumed pdfium work even though it failed).
        """
        cls._ensure_worker(should_pause)

        # Pre-check: recycle BEFORE the batch that would exceed budget.
        if cls._page_counter > 0 and cls._page_counter + expected_pages > _MARKER_WORKER_MAX_PAGES:
            cls._log("recycle", f"page budget reached ({cls._page_counter} + {expected_pages} > {_MARKER_WORKER_MAX_PAGES})")
            cls._shutdown_worker()
            cls._ensure_worker(should_pause)

        cls._job_counter += 1
        job = cls._job_counter
        retried = False

        while True:
            try:
                cls._send({"job": job, "pdf": pdf_path})
            except (BrokenPipeError, OSError) as e:
                if not retried:
                    cls._log("crash", f"worker dead before send ({e}), retrying")
                    cls._proc = None
                    cls._queue = None
                    cls._ensure_worker(should_pause)
                    cls._job_counter += 1
                    job = cls._job_counter
                    retried = True
                    continue
                raise RuntimeError(
                    f"Marker worker crashed twice before send.\n"
                    f"stderr tail:\n{''.join(cls._stderr_lines)}"
                ) from e

            response = cls._wait_for_response(job, should_pause)
            if response is None:
                stderr_tail = "".join(cls._stderr_lines)
                cls._proc = None
                cls._queue = None
                if retried:
                    raise RuntimeError(
                        f"Marker worker crashed twice on same batch.\n"
                        f"stderr tail:\n{stderr_tail}"
                    )
                cls._log("crash", f"worker died mid-task, retrying")
                cls._ensure_worker(should_pause)
                cls._job_counter += 1
                job = cls._job_counter
                retried = True
                continue

            if response.get("ok"):
                elements = [_decode_element(e) for e in response["elements"]]
                section_count = response.get("section_count", 0)
                cls._page_counter += expected_pages
                return elements, section_count
            else:
                cls._page_counter += expected_pages
                if cls._page_counter > _MARKER_WORKER_MAX_PAGES:
                    cls._shutdown_worker()
                raise RuntimeError(
                    f"Marker worker returned ok=false: {response.get('error', 'unknown')}"
                )

    @classmethod
    def shutdown(cls) -> None:
        """Idempotent graceful shutdown."""
        cls._shutdown_worker()

    # ── internals ───────────────────────────────────────────────────

    @classmethod
    def _ensure_worker(cls, should_pause: Callable[[], bool]) -> None:
        """Spawn a new worker if none is running, then wait for ready."""
        if cls._proc is not None and cls._proc.poll() is None:
            return

        cls._log("spawn", "starting marker worker")
        cls._proc = subprocess.Popen(
            [sys.executable, "-m", "pipeline.parse.marker_worker"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
        )
        cls._queue = queue.Queue()

        # Threads receive immutable references — never read cls._proc
        # or cls._queue from inside the thread after start.
        cls._stdout_thread = threading.Thread(
            target=cls._read_stdout,
            args=(cls._proc, cls._queue),
            daemon=True,
        )
        cls._stdout_thread.start()
        cls._stderr_thread = threading.Thread(
            target=cls._read_stderr,
            args=(cls._proc, cls._stderr_lines),
            daemon=True,
        )
        cls._stderr_thread.start()

        cls._page_counter = 0
        cls._job_counter = 0
        cls._page_sep = None
        cls._stderr_lines.clear()

        # Wait for ready handshake
        while True:
            try:
                msg = cls._queue.get(timeout=2)
            except queue.Empty:
                if should_pause():
                    cls._proc.kill()
                    cls._proc.communicate()
                    cls._proc = None
                    cls._queue = None
                    raise MarkerParsePaused("pause during worker startup")
                continue

            if msg is _EOF_SENTINEL:
                stderr_tail = "".join(cls._stderr_lines)
                cls._proc = None
                cls._queue = None
                raise RuntimeError(
                    f"Marker worker crashed during startup.\n"
                    f"stderr tail:\n{stderr_tail}"
                )

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            # Validate it's actually our ready message (not leaked library output)
            if isinstance(data, dict) and data.get("ready") is True:
                cls._page_sep = data.get("page_sep")
                break

    @classmethod
    def _send(cls, data: dict) -> None:
        line = json.dumps(data, ensure_ascii=False) + "\n"
        cls._proc.stdin.write(line)
        cls._proc.stdin.flush()

    @classmethod
    def _wait_for_response(cls, job: int, should_pause: Callable[[], bool]) -> dict | None:
        """Poll queue for the response matching `job`. Returns None if worker died."""
        while True:
            if cls._proc.poll() is not None:
                return None

            try:
                msg = cls._queue.get(timeout=2)
            except queue.Empty:
                if should_pause():
                    cls._proc.kill()
                    cls._proc.communicate()
                    cls._proc = None
                    cls._queue = None
                    raise MarkerParsePaused("pause during worker processing")
                continue

            if msg is _EOF_SENTINEL:
                return None

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            if isinstance(data, dict) and data.get("job") == job:
                return data

    @classmethod
    def _shutdown_worker(cls) -> None:
        """Gracefully shut down the worker, or kill if unresponsive."""
        if cls._proc is None or cls._proc.poll() is not None:
            cls._proc = None
            cls._queue = None
            return
        try:
            cls._send({"cmd": "shutdown"})
            cls._proc.wait(timeout=_SHUTDOWN_TIMEOUT_S)
        except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
            cls._proc.kill()
            cls._proc.communicate()
        finally:
            cls._proc = None
            cls._queue = None

    # ── reader threads (static — receive immutable args) ────────────

    @staticmethod
    def _read_stdout(proc: subprocess.Popen, q: queue.Queue) -> None:
        """Read lines from worker stdout into the queue."""
        try:
            for line in proc.stdout:
                q.put(line.strip())
        except (ValueError, OSError):
            pass
        finally:
            q.put(_EOF_SENTINEL)

    @staticmethod
    def _read_stderr(proc: subprocess.Popen, buf: collections.deque) -> None:
        """Accumulate stderr lines for crash diagnostics."""
        try:
            for line in proc.stderr:
                buf.append(line)
        except (ValueError, OSError):
            pass

    # ── lifecycle logging ───────────────────────────────────────────

    @classmethod
    def _log(cls, event: str, detail: str) -> None:
        pid = cls._proc.pid if cls._proc is not None else "?"
        print(f"[marker-worker] {event} (pid={pid}) {detail}")
