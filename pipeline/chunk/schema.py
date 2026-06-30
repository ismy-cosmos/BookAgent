from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Chunk:
    chunk_id: str
    book_id: str
    source_file: str
    element_type: str   # "text"|"table"|"formula"|"code"|"figure"|"audio"
    content: str
    token_count: int
    page_start: Optional[int] = None    # 1-indexed; None for audio/image
    start_sec: Optional[float] = None   # audio only
    end_sec: Optional[float] = None     # audio only
    low_confidence: bool = False        # audio only; True if avg word-level ASR score < 0.6
