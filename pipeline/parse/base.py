from __future__ import annotations
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# Figure/Table 说明行（如 "Figure 3.2: ..."）。chunker 的 caption-aware 拼接
# 与 VLM 批量描述的 prompt 上下文共用同一判定，必须保持单一定义。
CAPTION_RE = re.compile(r"^(Figure|Table)\s+[\d.]+\s*:", re.IGNORECASE)


@dataclass
class Element:
    type: str       # "text" | "table" | "formula" | "figure" | "code"
    content: str    # Markdown / LaTeX / plain text
    page_num: int   # 1-indexed
    metadata: dict = field(default_factory=dict)


class Parser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> list[Element]: ...
