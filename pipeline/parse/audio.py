from __future__ import annotations
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import tiktoken

from pipeline.chunk.schema import Chunk

_WHISPERX_PATH = os.environ.get(
    "WHISPERX_PATH",
    "/home/ismy/github/BookAgent-Baseline/audio/whisperx_env/bin/whisperx",
)
_ENC = None


def _enc():
    global _ENC
    if _ENC is None:
        _ENC = tiktoken.get_encoding("cl100k_base")
    return _ENC


class AudioParser:
    """Transcribe audio with WhisperX and map segments directly to Chunks."""

    def __init__(
        self,
        whisperx_path: str = _WHISPERX_PATH,
        model: str = "small",
        language: Optional[str] = None,
    ):
        self._wx = whisperx_path
        self._model = model
        self._lang = language

    def parse_to_chunks(self, audio_path: str, book_id: str, source_file: str = "") -> list[Chunk]:
        if not Path(self._wx).exists():
            raise RuntimeError(
                f"WhisperX 未找到：{self._wx}\n"
                f"请检查 WHISPERX_PATH 环境变量，或确认 whisperx 已正确安装到该路径。"
            )

        resolved_name = source_file or Path(audio_path).name
        stem = Path(audio_path).stem

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                self._wx, audio_path,
                "--model", self._model,
                "--output_dir", tmpdir,
                "--output_format", "json",
            ]
            if self._lang is not None:
                cmd.extend(["--language", self._lang])
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            out_file = Path(tmpdir) / f"{stem}.json"
            data = json.loads(out_file.read_text())

        chunks: list[Chunk] = []
        for seq, seg in enumerate(data.get("segments", [])):
            text = seg["text"].strip()
            if not text:
                continue
            chunk_id = f"{book_id}/{Path(resolved_name).stem}/{seq:04d}"
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
