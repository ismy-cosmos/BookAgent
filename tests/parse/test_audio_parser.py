import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from pipeline.parse.audio import AudioParser


def _fake_whisperx_run(cmd, tmpdir, stem):
    """Helper: simulate whisperx creating output JSON."""
    out = {
        "segments": [
            {"start": 74.0, "end": 101.0, "text": "There are 340 processes."},
            {"start": 196.0, "end": 218.0, "text": "The spin function calls getTime."},
        ]
    }
    (Path(tmpdir) / f"{stem}.json").write_text(json.dumps(out))


def test_audio_parser_returns_chunks(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    def fake_run(cmd, check, **kwargs):
        _fake_whisperx_run(cmd, cmd[cmd.index("--output_dir") + 1], "segment-01")

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        parser = AudioParser()
        chunks = parser.parse_to_chunks(str(audio), book_id="ostep")

    assert len(chunks) == 2
    assert chunks[0].start_sec == 74.0
    assert chunks[0].end_sec == 101.0
    assert "340 processes" in chunks[0].content


def test_audio_parser_chunk_ids(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    def fake_run(cmd, check, **kwargs):
        _fake_whisperx_run(cmd, cmd[cmd.index("--output_dir") + 1], "segment-01")

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="ostep")

    assert chunks[0].chunk_id == "ostep/segment-01/0000"
    assert chunks[1].chunk_id == "ostep/segment-01/0001"


def test_audio_parser_chunk_fields(tmp_path):
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"fake")

    def fake_run(cmd, check, **kwargs):
        out = {"segments": [{"start": 0.0, "end": 5.0, "text": "Hello."}]}
        (Path(cmd[cmd.index("--output_dir") + 1]) / "lecture.json").write_text(json.dumps(out))

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    c = chunks[0]
    assert c.book_id == "b"
    assert c.source_file == "lecture.mp3"
    assert c.element_type == "audio"
    assert c.page_start is None
    assert c.token_count > 0


def test_audio_parser_empty_segments(tmp_path):
    audio = tmp_path / "empty.mp3"
    audio.write_bytes(b"fake")

    def fake_run(cmd, check, **kwargs):
        out = {"segments": []}
        (Path(cmd[cmd.index("--output_dir") + 1]) / "empty.json").write_text(json.dumps(out))

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert chunks == []
