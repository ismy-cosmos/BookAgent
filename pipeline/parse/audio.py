from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import tiktoken

from pipeline.chunk.schema import Chunk

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_WHISPERX_VENV_PYTHON = os.environ.get(
    "WHISPERX_VENV_PYTHON",
    str(_REPO_ROOT / "whisperx.venv" / "bin" / "python"),
)
_WHISPERX_WRAPPER = str(Path(__file__).resolve().parent / "whisperx_transcribe.py")
_ENC = None


def _enc():
    global _ENC
    if _ENC is None:
        _ENC = tiktoken.get_encoding("cl100k_base")
    return _ENC


class AudioParser:
    """Transcribe audio with WhisperX (isolated venv) and map segments directly to Chunks."""

    def __init__(
        self,
        whisperx_python: str = _WHISPERX_VENV_PYTHON,
        model: str = "small",
        language: Optional[str] = None,
    ):
        self._wx_python = whisperx_python
        self._model = model
        self._lang = language

    def parse_to_chunks(self, audio_path: str, book_id: str, source_file: str = "") -> list[Chunk]:
        if not Path(self._wx_python).exists():
            raise RuntimeError(
                f"WhisperX venv 未找到：{self._wx_python}\n"
                f"请运行 setup.sh 安装 whisperx 环境，或检查 WHISPERX_VENV_PYTHON 环境变量。"
            )

        resolved_name = source_file or Path(audio_path).name

        cmd = [self._wx_python, _WHISPERX_WRAPPER, audio_path, "--model", self._model]
        if self._lang is not None:
            cmd.extend(["--language", self._lang])
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"WhisperX wrapper 输出不是合法 JSON: {result.stdout[:500]!r}"
            ) from e

        chunks: list[Chunk] = []
        for seq, seg in enumerate(data.get("segments", [])):
            text = seg["text"].strip()
            if not text:
                continue
            chunk_id = f"{book_id}/{Path(resolved_name).name}/{seq:04d}"
            words = seg.get("words", [])
            scores = [w["score"] for w in words if "score" in w]
            avg_score = sum(scores) / len(scores) if scores else 1.0
            chunks.append(Chunk(
                chunk_id=chunk_id,
                book_id=book_id,
                source_file=resolved_name,
                element_type="audio",
                content=text,
                token_count=len(_enc().encode(text)),
                page_start=None,
                start_sec=float(seg["start"]),
                end_sec=float(seg["end"]),
                low_confidence=avg_score < 0.6,
            ))
        return chunks