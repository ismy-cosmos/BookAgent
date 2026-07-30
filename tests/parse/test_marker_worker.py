"""Tests for marker_worker.py — PdfConverter is mocked; no model weights loaded."""
import json
import io
import sys
from unittest.mock import MagicMock, patch

import pytest


def _run_worker(stdin_lines: list[str]) -> list[dict]:
    stdin = io.StringIO("\n".join(stdin_lines) + "\n")
    stdout = io.StringIO()

    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        # PdfConverter is imported inside main(), patch at its real module path
        with patch("marker.converters.pdf.PdfConverter") as MockConverter, \
             patch("marker.models.create_model_dict", return_value={}):
            mock_converter = MockConverter.return_value
            mock_converter.resolve_dependencies.return_value.page_separator = "@@BOOKAGENT_PAGE_BREAK@@"
            rendered = MagicMock()
            rendered.markdown = "{0}\n\n@@BOOKAGENT_PAGE_BREAK@@\n\nTest content."
            rendered.images = {}
            mock_converter.return_value = rendered

            from pipeline.parse.marker_worker import main
            main()

    lines = [line.strip() for line in stdout.getvalue().splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def test_worker_emits_ready_with_page_sep():
    responses = _run_worker(['{"cmd": "shutdown"}'])
    assert responses[0]["ready"] is True
    assert "page_sep" in responses[0]


def test_worker_processes_single_job():
    responses = _run_worker([
        '{"job": 1, "pdf": "/fake/path.pdf"}',
        '{"cmd": "shutdown"}',
    ])
    assert responses[0]["ready"] is True
    assert responses[1]["job"] == 1
    assert responses[1]["ok"] is True
    assert isinstance(responses[1]["elements"], list)
    assert "section_count" in responses[1]


def test_worker_handles_multiple_jobs():
    responses = _run_worker([
        '{"job": 1, "pdf": "/fake/a.pdf"}',
        '{"job": 2, "pdf": "/fake/b.pdf"}',
        '{"cmd": "shutdown"}',
    ])
    assert len(responses) == 3


def test_worker_ok_false_on_render_error():
    stdin = io.StringIO('{"job": 1, "pdf": "/fake/bad.pdf"}\n{"cmd": "shutdown"}\n')
    stdout = io.StringIO()

    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        with patch("marker.converters.pdf.PdfConverter") as MockConverter, \
             patch("marker.models.create_model_dict", return_value={}):
            mock_converter = MockConverter.return_value
            mock_converter.resolve_dependencies.return_value.page_separator = "@@BP@@"
            # Constructor succeeds (ready emitted), calling the instance fails
            mock_converter.side_effect = RuntimeError("rendering failed")

            from pipeline.parse.marker_worker import main
            main()

    lines = [line.strip() for line in stdout.getvalue().splitlines() if line.strip()]
    responses = [json.loads(line) for line in lines]
    assert responses[0]["ready"] is True
    assert responses[1]["job"] == 1
    assert responses[1]["ok"] is False
    assert "RuntimeError" in responses[1]["error"]


def test_worker_exits_on_stdin_eof():
    stdin = io.StringIO("")
    stdout = io.StringIO()

    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        with patch("marker.converters.pdf.PdfConverter") as MockConverter, \
             patch("marker.models.create_model_dict", return_value={}):
            mock_converter = MockConverter.return_value
            mock_converter.resolve_dependencies.return_value.page_separator = "@@BP@@"
            from pipeline.parse.marker_worker import main
            main()

    lines = [line.strip() for line in stdout.getvalue().splitlines() if line.strip()]
    responses = [json.loads(line) for line in lines]
    assert len(responses) == 1
    assert responses[0]["ready"] is True


def test_worker_ignores_empty_lines_and_invalid_json():
    responses = _run_worker([
        "",
        "   ",
        "not json",
        '{"job": 1, "pdf": "/fake/path.pdf"}',
        "",
        '{"cmd": "shutdown"}',
    ])
    assert len(responses) == 2  # ready + job response
