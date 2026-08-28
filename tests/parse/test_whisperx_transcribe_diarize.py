# tests/parse/test_whisperx_transcribe_diarize.py
"""这个测试文件必须用 whisperx.venv 的 python 跑：
whisperx.venv/bin/python -m pytest tests/parse/test_whisperx_transcribe_diarize.py -v
因为要 mock 的 whisperx/pyannote 只装在 whisperx.venv 里，bookagent.venv 没有。

不能用 `from pipeline.parse.whisperx_transcribe import transcribe`：这会触发
Python 先执行 pipeline/parse/__init__.py（父包初始化），而那个文件会连带
import MarkerParser/EPUBParser/VLMImageParser，需要 pypdfium2/marker-pdf 等一整套
重依赖——这些只装在 bookagent.venv，whisperx.venv 里没有。但 whisperx_transcribe.py
本身在生产环境里是被当作独立脚本子进程调用的（AudioParser 用 subprocess.Popen 直接
跑 `whisperx.venv/bin/python .../whisperx_transcribe.py`），从来不是被当成包的子模块
import 的，文件本身在模块顶层也确实没有任何 pipeline.* 依赖。所以这里改用
importlib 按文件路径直接加载，绕开父包 __init__.py，跟真实调用方式保持一致。
"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# whisperx 只装在 whisperx.venv，不装在 bookagent.venv——用 bookagent.venv 跑
# `pytest tests/`（项目日常/CI 用的命令）时，这个文件必须整体跳过而不是报失败，
# 不能让只该在 whisperx.venv 里跑的测试拖垮主 venv 的测试基线。
pytest.importorskip("whisperx")

_MODULE_PATH = Path(__file__).resolve().parent.parent.parent / "pipeline" / "parse" / "whisperx_transcribe.py"
_spec = importlib.util.spec_from_file_location("whisperx_transcribe", _MODULE_PATH)
_wt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wt)
transcribe = _wt.transcribe


def _fake_whisperx_model():
    model = MagicMock()
    model.transcribe.return_value = {
        "language": "en",
        "segments": [{"start": 0.0, "end": 2.0, "text": "Hello."}],
    }
    return model


def _fake_aligned():
    return {
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "Hello.", "words": [{"word": "Hello.", "score": 0.9}]},
        ]
    }


def test_diarize_false_no_speaker_key_default_unchanged():
    with patch("whisperx.load_model", return_value=_fake_whisperx_model()), \
         patch("whisperx.load_audio", return_value="fake_audio_array"), \
         patch("whisperx.load_align_model", return_value=(MagicMock(), MagicMock())), \
         patch("whisperx.align", return_value=_fake_aligned()), \
         patch("torch.cuda.is_available", return_value=False):
        result = transcribe("fake.mp3", "small", None, diarize=False)

    assert "speaker" not in result["segments"][0]


def test_diarize_true_adds_speaker_key():
    fake_diarize_df = "FAKE_DIARIZE_DF"
    fake_pipeline_instance = MagicMock()
    fake_pipeline_instance.return_value = fake_diarize_df

    def fake_assign_word_speakers(diarize_df, transcript_result, fill_nearest=False):
        assert diarize_df == fake_diarize_df
        assert fill_nearest is True
        transcript_result["segments"][0]["speaker"] = "SPEAKER_00"
        return transcript_result

    # 注意：patch 目标是 whisperx.diarize 这个真实模块的属性，不是
    # pipeline.parse.whisperx_transcribe 里的模块级别名——因为实现刻意把
    # `from whisperx.diarize import ...` 放在 if diarize: 分支内部（懒加载，
    # 避免默认路径背上pyannote约2秒的导入开销），模块顶层不存在这两个名字可patch。
    with patch("whisperx.load_model", return_value=_fake_whisperx_model()), \
         patch("whisperx.load_audio", return_value="fake_audio_array"), \
         patch("whisperx.load_align_model", return_value=(MagicMock(), MagicMock())), \
         patch("whisperx.align", return_value=_fake_aligned()), \
         patch("torch.cuda.is_available", return_value=False), \
         patch("whisperx.diarize.DiarizationPipeline",
               return_value=fake_pipeline_instance), \
         patch("whisperx.diarize.assign_word_speakers",
               side_effect=fake_assign_word_speakers):
        result = transcribe("fake.mp3", "small", None, diarize=True)

    assert result["segments"][0]["speaker"] == "SPEAKER_00"
