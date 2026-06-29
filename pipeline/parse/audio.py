from __future__ import annotations
import json
import os
import subprocess
import tempfile
from pathlib import Path

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
        model: str = "base",
        language: str = "zh",
    ):
        self._wx = whisperx_path
        self._model = model
        self._lang = language

    def parse_to_chunks(self, audio_path: str, book_id: str) -> list[Chunk]:
        source_file = Path(audio_path).name
        stem = Path(audio_path).stem

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                self._wx, audio_path,
                "--model", self._model,
                "--language", self._lang,
                "--output_dir", tmpdir,
                "--output_format", "json",
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            out_file = Path(tmpdir) / f"{stem}.json"
            data = json.loads(out_file.read_text())

        chunks: list[Chunk] = []
        for seq, seg in enumerate(data.get("segments", [])):
            text = seg["text"].strip()
            if not text:
                continue
            chunk_id = f"{book_id}/{stem}/{seq:04d}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                book_id=book_id,
                source_file=source_file,
                element_type="audio",
                content=text,
                token_count=len(_enc().encode(text)),
                page_start=None,
                start_sec=float(seg["start"]),
                end_sec=float(seg["end"]),
            ))
        return chunks
