from __future__ import annotations
import os


def get_chroma_dir() -> str:
    return os.environ.get("CHROMA_DIR", ".chroma")
