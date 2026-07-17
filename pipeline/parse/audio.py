from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Optional

from pipeline.chunk.schema import Chunk

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_WHISPERX_VENV_PYTHON = os.environ.get(
    "WHISPERX_VENV_PYTHON",
    str(_REPO_ROOT / "whisperx.venv" / "bin" / "python"),
)
_WHISPERX_WRAPPER = str(Path(__file__).resolve().parent / "whisperx_transcribe.py")
_DEFAULT_POLL_INTERVAL_S = 2.0


def _always_false() -> bool:
    return False


class AudioParsePaused(RuntimeError):
    """转写过程中收到暂停请求，子进程已被终止——这个文件的转写工作完全
    作废（WhisperX 不支持流式吐出部分结果），没有部分结果可用。"""


class AudioParser:
    """Transcribe audio with WhisperX (isolated venv) and map segments directly to Chunks."""

    def __init__(
        self,
        whisperx_python: str = _WHISPERX_VENV_PYTHON,
        model: str = "small",
        language: Optional[str] = None,
        poll_interval_s: float = _DEFAULT_POLL_INTERVAL_S,
    ):
        self._wx_python = whisperx_python
        self._model = model
        self._lang = language
        self._poll_interval_s = poll_interval_s

    def parse_to_chunks(
        self,
        audio_path: str,
        book_id: str,
        source_file: str = "",
        should_pause: Callable[[], bool] = _always_false,
    ) -> list[Chunk]:
        if not Path(self._wx_python).exists():
            raise RuntimeError(
                f"WhisperX venv 未找到：{self._wx_python}\n"
                f"请运行 setup.sh 安装 whisperx 环境，或检查 WHISPERX_VENV_PYTHON 环境变量。"
            )

        resolved_name = source_file or Path(audio_path).name

        cmd = [self._wx_python, _WHISPERX_WRAPPER, audio_path, "--model", self._model]
        if self._lang is not None:
            cmd.extend(["--language", self._lang])

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=self._poll_interval_s)
                break
            except subprocess.TimeoutExpired:
                if should_pause():
                    proc.kill()
                    proc.communicate()
                    raise AudioParsePaused(f"暂停请求中止了音频转写：{audio_path}")

        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=stderr)

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"WhisperX wrapper 输出不是合法 JSON: {stdout[:500]!r}"
            ) from e

        raw_segments = []
        for seg in data.get("segments", []):
            words = seg.get("words", [])
            scores = [w["score"] for w in words if "score" in w]
            avg_score = sum(scores) / len(scores) if scores else 1.0
            raw_segments.append({
                "text": seg["text"],
                "start": float(seg["start"]),
                "end": float(seg["end"]),
                "score": avg_score,
            })
        # 延迟到调用时才导入：chunker.py 顶部 import 了 pipeline.parse.base，
        # 而 pipeline/parse/__init__.py 又预加载了本模块（audio.py）——放在
        # 模块顶层会形成循环导入，函数体内导入这时 chunker 模块已经加载完毕。
        from pipeline.chunk.chunker import pack_audio_segments
        return pack_audio_segments(raw_segments, book_id, resolved_name)
