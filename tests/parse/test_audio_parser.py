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


def test_audio_parser_default_language_is_auto_detect(tmp_path):
    """默认不应该传 --language，让 whisperx 自动检测语种（与设计文档要求一致）。"""
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    captured_cmd = []

    def fake_run(cmd, check, **kwargs):
        captured_cmd.extend(cmd)
        _fake_whisperx_run(cmd, cmd[cmd.index("--output_dir") + 1], "segment-01")

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        AudioParser().parse_to_chunks(str(audio), book_id="ostep")

    assert "--language" not in captured_cmd


def test_audio_parser_explicit_language_still_works(tmp_path):
    """显式指定语种时，--language 仍应正确传给 whisperx。"""
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    captured_cmd = []

    def fake_run(cmd, check, **kwargs):
        captured_cmd.extend(cmd)
        _fake_whisperx_run(cmd, cmd[cmd.index("--output_dir") + 1], "segment-01")

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        AudioParser(language="en").parse_to_chunks(str(audio), book_id="ostep")

    assert "--language" in captured_cmd
    assert captured_cmd[captured_cmd.index("--language") + 1] == "en"


def test_audio_parser_default_model_is_small(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    captured_cmd = []

    def fake_run(cmd, check, **kwargs):
        captured_cmd.extend(cmd)
        _fake_whisperx_run(cmd, cmd[cmd.index("--output_dir") + 1], "segment-01")

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        AudioParser().parse_to_chunks(str(audio), book_id="ostep")

    assert captured_cmd[captured_cmd.index("--model") + 1] == "small"


def test_audio_parser_raises_clear_error_when_whisperx_missing(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    parser = AudioParser(whisperx_path="/nonexistent/path/to/whisperx")
    with pytest.raises(RuntimeError, match="WhisperX"):
        parser.parse_to_chunks(str(audio), book_id="ostep")


def test_audio_parser_low_confidence_segment_flagged(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    def fake_run(cmd, check, **kwargs):
        out = {
            "segments": [
                {
                    "start": 0.0, "end": 5.0, "text": "Mumbled audio.",
                    "words": [{"word": "Mumbled", "score": 0.3}, {"word": "audio.", "score": 0.4}],
                },
            ]
        }
        (Path(cmd[cmd.index("--output_dir") + 1]) / "segment-01.json").write_text(json.dumps(out))

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert chunks[0].low_confidence is True


def test_audio_parser_high_confidence_segment_not_flagged(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    def fake_run(cmd, check, **kwargs):
        out = {
            "segments": [
                {
                    "start": 0.0, "end": 5.0, "text": "Clear audio.",
                    "words": [{"word": "Clear", "score": 0.95}, {"word": "audio.", "score": 0.9}],
                },
            ]
        }
        (Path(cmd[cmd.index("--output_dir") + 1]) / "segment-01.json").write_text(json.dumps(out))

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert chunks[0].low_confidence is False


def test_audio_parser_no_word_scores_defaults_not_low_confidence(tmp_path):
    """没有 words 字段时（比如关闭了对齐），不应该被误判为低置信度。"""
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    def fake_run(cmd, check, **kwargs):
        _fake_whisperx_run(cmd, cmd[cmd.index("--output_dir") + 1], "segment-01")

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert chunks[0].low_confidence is False


def test_audio_parser_seq_skips_blank_segments(tmp_path):
    audio = tmp_path / "mixed.mp3"
    audio.write_bytes(b"fake")

    def fake_run(cmd, check, **kwargs):
        out = {
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Hello."},
                {"start": 5.0, "end": 8.0, "text": "   "},   # 空白，跳过
                {"start": 8.0, "end": 12.0, "text": "World."},
            ]
        }
        (Path(cmd[cmd.index("--output_dir") + 1]) / "mixed.json").write_text(json.dumps(out))

    with patch("pipeline.parse.audio.subprocess.run", side_effect=fake_run):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert len(chunks) == 2
    assert chunks[0].chunk_id == "b/mixed/0000"
    # seq 使用 WhisperX 原始 segment index，空 segment 被跳过时出现跳号
    # 此处 segment index 1 为空，故第二个有效 chunk 的 seq=2 而非 seq=1
    assert chunks[1].chunk_id.endswith("/0002")
    assert not chunks[1].chunk_id.endswith("/0001")
    assert "Hello" in chunks[0].content
    assert "World" in chunks[1].content
