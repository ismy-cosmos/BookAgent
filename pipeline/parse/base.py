from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Element:
    type: str       # "text" | "table" | "formula" | "figure" | "code"
    content: str    # Markdown / LaTeX / plain text
    page_num: int   # 1-indexed
    metadata: dict = field(default_factory=dict)


class Parser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> list[Element]: ...
