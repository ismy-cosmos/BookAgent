import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from pipeline.parse.audio import AudioParser, AudioParsePaused


def _fake_popen(segments, returncode=0, stderr=""):
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (json.dumps({"segments": segments}), stderr)
    mock_proc.returncode = returncode
    return mock_proc


def test_audio_parser_merges_small_segments_into_one_chunk(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    segments = [
        {"start": 74.0, "end": 101.0, "text": "There are 340 processes."},
        {"start": 196.0, "end": 218.0, "text": "The spin function calls getTime."},
    ]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        parser = AudioParser()
        chunks = parser.parse_to_chunks(str(audio), book_id="ostep")

    # 两个短segment远低于256 token目标，会被打包合并成一个chunk
    assert len(chunks) == 1
    assert chunks[0].start_sec == 74.0
    assert chunks[0].end_sec == 218.0
    assert "340 processes" in chunks[0].content
    assert "getTime" in chunks[0].content


def test_audio_parser_splits_into_multiple_chunks_past_token_limit(tmp_path):
    audio = tmp_path / "long-lecture.mp3"
    audio.write_bytes(b"fake")

    long_text = "This is a segment about operating system scheduling policies. " * 20
    segments = [
        {"start": 0.0, "end": 30.0, "text": long_text},
        {"start": 30.0, "end": 60.0, "text": long_text},
    ]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        parser = AudioParser()
        chunks = parser.parse_to_chunks(str(audio), book_id="ostep")

    assert len(chunks) == 2
    assert chunks[0].start_sec == 0.0
    assert chunks[0].end_sec == 30.0
    assert chunks[1].start_sec == 30.0
    assert chunks[1].end_sec == 60.0


def test_audio_parser_chunk_ids_sequential_by_output_not_input_index(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    long_text = "This is a segment about operating system scheduling policies. " * 20
    segments = [
        {"start": 0.0, "end": 30.0, "text": long_text},
        {"start": 30.0, "end": 60.0, "text": long_text},
    ]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="ostep")

    assert chunks[0].chunk_id == "ostep/segment-01.mp3/0000"
    assert chunks[1].chunk_id == "ostep/segment-01.mp3/0001"


def test_audio_parser_chunk_fields(tmp_path):
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"fake")

    segments = [{"start": 0.0, "end": 5.0, "text": "Hello."}]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
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

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen([])):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert chunks == []


def test_audio_parser_default_language_is_auto_detect(tmp_path):
    """默认不应该传 --language，让 whisperx 自动检测语种。"""
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    segments = [{"start": 74.0, "end": 101.0, "text": "There are 340 processes."}]
    captured_cmd = []

    def fake_popen(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return _fake_popen(segments)

    with patch("pipeline.parse.audio.subprocess.Popen", side_effect=fake_popen):
        AudioParser().parse_to_chunks(str(audio), book_id="ostep")

    assert "--language" not in captured_cmd


def test_audio_parser_explicit_language_still_works(tmp_path):
    """显式指定语种时，--language 仍应正确传给 whisperx。"""
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    segments = [{"start": 74.0, "end": 101.0, "text": "There are 340 processes."}]
    captured_cmd = []

    def fake_popen(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return _fake_popen(segments)

    with patch("pipeline.parse.audio.subprocess.Popen", side_effect=fake_popen):
        AudioParser(language="en").parse_to_chunks(str(audio), book_id="ostep")

    assert "--language" in captured_cmd
    assert captured_cmd[captured_cmd.index("--language") + 1] == "en"


def test_audio_parser_default_model_is_small(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    segments = [{"start": 74.0, "end": 101.0, "text": "There are 340 processes."}]
    captured_cmd = []

    def fake_popen(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return _fake_popen(segments)

    with patch("pipeline.parse.audio.subprocess.Popen", side_effect=fake_popen):
        AudioParser().parse_to_chunks(str(audio), book_id="ostep")

    assert captured_cmd[captured_cmd.index("--model") + 1] == "small"


def test_audio_parser_raises_clear_error_when_whisperx_missing(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    parser = AudioParser(whisperx_python="/nonexistent/path/to/python")
    with pytest.raises(RuntimeError, match="WhisperX venv"):
        parser.parse_to_chunks(str(audio), book_id="ostep")


def test_audio_parser_low_confidence_segment_flagged(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    segments = [
        {
            "start": 0.0, "end": 5.0, "text": "Mumbled audio.",
            "words": [{"word": "Mumbled", "score": 0.3}, {"word": "audio.", "score": 0.4}],
        },
    ]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert chunks[0].low_confidence is True


def test_audio_parser_high_confidence_segment_not_flagged(tmp_path):
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    segments = [
        {
            "start": 0.0, "end": 5.0, "text": "Clear audio.",
            "words": [{"word": "Clear", "score": 0.95}, {"word": "audio.", "score": 0.9}],
        },
    ]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert chunks[0].low_confidence is False


def test_audio_parser_no_word_scores_defaults_not_low_confidence(tmp_path):
    """没有 words 字段时（比如关闭了对齐），不应该被误判为低置信度。"""
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    segments = [{"start": 74.0, "end": 101.0, "text": "There are 340 processes."}]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    assert chunks[0].low_confidence is False


def test_audio_parser_blank_segment_skipped_time_span_still_correct(tmp_path):
    audio = tmp_path / "mixed.mp3"
    audio.write_bytes(b"fake")

    segments = [
        {"start": 0.0, "end": 5.0, "text": "Hello."},
        {"start": 5.0, "end": 8.0, "text": "   "},
        {"start": 8.0, "end": 12.0, "text": "World."},
    ]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        chunks = AudioParser().parse_to_chunks(str(audio), book_id="b")

    # "Hello."和"World."远低于256 token目标，会合并成一个chunk；
    # 中间的空白segment被跳过，不出现在content里，也不打断合并
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "b/mixed.mp3/0000"
    assert chunks[0].start_sec == 0.0
    assert chunks[0].end_sec == 12.0
    assert "Hello" in chunks[0].content
    assert "World" in chunks[0].content


def test_audio_parser_wrapper_bad_json_raises_clear_error(tmp_path):
    """wrapper 脚本输出不是合法 JSON 时，应抛出带原始输出片段的清晰错误。"""
    audio = tmp_path / "segment-01.mp3"
    audio.write_bytes(b"fake")

    bad_proc = MagicMock()
    bad_proc.communicate.return_value = ("INFO: some log line leaked\n{\"segments\": []}", "")
    bad_proc.returncode = 0

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=bad_proc):
        with pytest.raises(RuntimeError, match="不是合法 JSON"):
            AudioParser().parse_to_chunks(str(audio), book_id="b")


def test_audio_parser_nonzero_exit_raises(tmp_path):
    audio = tmp_path / "bad.mp3"
    audio.write_bytes(b"fake")
    mock_proc = _fake_popen([], returncode=1, stderr="whisperx crashed")

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=mock_proc):
        with pytest.raises(subprocess.CalledProcessError):
            AudioParser().parse_to_chunks(str(audio), book_id="b")


# ── 暂停：Popen + 轮询 + kill ────────────────────────────────────────────

def test_audio_parser_pause_kills_process_and_raises(tmp_path):
    audio = tmp_path / "long.mp3"
    audio.write_bytes(b"fake")

    mock_proc = MagicMock()
    mock_proc.communicate.side_effect = [
        subprocess.TimeoutExpired(cmd="x", timeout=0.01),
        ("", ""),  # kill 后的收尾 communicate()
    ]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=mock_proc):
        with pytest.raises(AudioParsePaused):
            AudioParser(poll_interval_s=0.01).parse_to_chunks(
                str(audio), book_id="b", should_pause=lambda: True)

    mock_proc.kill.assert_called_once()


def test_audio_parser_no_pause_requested_completes_normally(tmp_path):
    audio = tmp_path / "short.mp3"
    audio.write_bytes(b"fake")
    segments = [{"start": 0.0, "end": 1.0, "text": "hi"}]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        chunks = AudioParser().parse_to_chunks(
            str(audio), book_id="b", should_pause=lambda: False)

    assert len(chunks) == 1


def test_audio_parser_pause_polls_multiple_times_before_pausing(tmp_path):
    """should_pause 一开始返回 False，过几轮才返回 True——确认是真的在轮询,不是只看一次。"""
    audio = tmp_path / "long.mp3"
    audio.write_bytes(b"fake")

    mock_proc = MagicMock()
    mock_proc.communicate.side_effect = [
        subprocess.TimeoutExpired(cmd="x", timeout=0.01),
        subprocess.TimeoutExpired(cmd="x", timeout=0.01),
        ("", ""),
    ]
    pause_calls = []

    def fake_should_pause():
        pause_calls.append(1)
        return len(pause_calls) >= 2

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=mock_proc):
        with pytest.raises(AudioParsePaused):
            AudioParser(poll_interval_s=0.01).parse_to_chunks(
                str(audio), book_id="b", should_pause=fake_should_pause)

    assert len(pause_calls) == 2


# ── issue #56: diarize 参数透传 ─────────────────────────────────────────────

def test_audio_parser_diarize_flag_passed_to_subprocess(tmp_path):
    audio = tmp_path / "hearing.mp3"
    audio.write_bytes(b"fake")

    segments = [{"start": 0.0, "end": 5.0, "text": "Hello.", "speaker": "SPEAKER_00"}]
    captured_cmd = []

    def fake_popen(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return _fake_popen(segments)

    with patch("pipeline.parse.audio.subprocess.Popen", side_effect=fake_popen):
        AudioParser(diarize=True).parse_to_chunks(str(audio), book_id="law")

    assert "--diarize" in captured_cmd


def test_audio_parser_diarize_false_default_no_flag_passed(tmp_path):
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"fake")

    segments = [{"start": 0.0, "end": 5.0, "text": "Hello."}]
    captured_cmd = []

    def fake_popen(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return _fake_popen(segments)

    with patch("pipeline.parse.audio.subprocess.Popen", side_effect=fake_popen):
        AudioParser().parse_to_chunks(str(audio), book_id="ostep")

    assert "--diarize" not in captured_cmd


def test_audio_parser_speaker_field_reaches_pack_audio_segments(tmp_path):
    """speaker 字段要真的传进 pack_audio_segments，体现在 chunk content 的 [SPEAKER_XX] 标签里。"""
    audio = tmp_path / "hearing.mp3"
    audio.write_bytes(b"fake")

    segments = [
        {"start": 0.0, "end": 2.0, "text": "Question one.", "speaker": "SPEAKER_00"},
        {"start": 2.0, "end": 4.0, "text": "Answer one.", "speaker": "SPEAKER_01"},
    ]

    with patch("pipeline.parse.audio.subprocess.Popen", return_value=_fake_popen(segments)):
        chunks = AudioParser(diarize=True).parse_to_chunks(str(audio), book_id="law")

    assert len(chunks) == 1
    assert "[SPEAKER_00] Question one." in chunks[0].content
    assert "[SPEAKER_01] Answer one." in chunks[0].content
