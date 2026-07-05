from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Citation:
    chunk_id: str
    source_file: str
    element_type: str
    citation: str
    score: Optional[float]


@dataclass
class ChatTurn:
    question: str
    answer: str
    citations: list[Citation] = field(default_factory=list)