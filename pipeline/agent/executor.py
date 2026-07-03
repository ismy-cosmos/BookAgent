from __future__ import annotations

import ast
import dataclasses
import json
from decimal import Decimal, InvalidOperation
from typing import Protocol, runtime_checkable

from pipeline.embed import Embedder
from pipeline.store import ChromaStore

# ── Stub data fixture ─────────────────────────────────────────────────────────

_STUB_CHUNKS = [
    {
        "chunk_id": "stub-001",
        "book_title": "深度学习（示例书）",
        "page_num": 42,
        "chapter": "第三章 注意力机制",
        "content": "注意力机制的核心公式为 Attention(Q,K,V)=softmax(QK^T/√d_k)V，"
                   "其中 Q、K、V 分别为查询、键和值矩阵，d_k 为键向量维度。"
                   "该机制允许模型在生成每个词时动态关注输入序列的不同位置。",
        "relevance_score": 0.93,
        "source_path": "/data/books/deep_learning.pdf",
    },
    {
        "chunk_id": "stub-002",
        "book_title": "深度学习（示例书）",
        "page_num": 17,
        "chapter": "第一章 神经网络基础",
        "content": "卷积神经网络（CNN）通过局部感受野和权值共享减少参数量。"
                   "典型结构包含卷积层、池化层和全连接层。"
                   "LeNet、AlexNet、VGG、ResNet 是里程碑式架构。",
        "relevance_score": 0.87,
        "source_path": "/data/books/deep_learning.pdf",
    },
    {
        "chunk_id": "stub-003",
        "book_title": "深度学习（示例书）",
        "page_num": 89,
        "chapter": "第五章 训练技巧",
        "content": "梯度消失问题在深层网络中尤为突出，反向传播时梯度指数衰减。"
                   "解决方法包括使用 ReLU 激活函数、残差连接（ResNet）和批归一化。",
        "relevance_score": 0.81,
        "source_path": "/data/books/deep_learning.pdf",
    },
    {
        "chunk_id": "stub-004",
        "book_title": "临床医学（示例书）",
        "page_num": 203,
        "chapter": "第八章 药物剂量计算",
        "content": "成人常用药物剂量计算公式：剂量(mg) = 体重(kg) × 单位剂量(mg/kg)。"
                   "儿童剂量需根据体重或体表面积折算，注意不超过成人剂量上限。",
        "relevance_score": 0.76,
        "source_path": "/data/books/clinical_medicine.pdf",
    },
    {
        "chunk_id": "stub-005",
        "book_title": "临床医学（示例书）",
        "page_num": 54,
        "chapter": "第二章 医学伦理",
        "content": "医学伦理四项基本原则：自主原则（尊重患者自主决定）、"
                   "不伤害原则、有利原则（以患者利益为先）、公正原则（资源公平分配）。",
        "relevance_score": 0.72,
        "source_path": "/data/books/clinical_medicine.pdf",
    },
    {
        "chunk_id": "stub-006",
        "book_title": "法学基础（示例书）",
        "page_num": 112,
        "chapter": "第四章 刑法总论",
        "content": "正当防卫是指为使国家、公共利益、本人或他人的人身、财产和其他权利"
                   "免受正在进行的不法侵害，采取的制止不法侵害的行为，造成损害的，"
                   "不负刑事责任。防卫过当应当负刑事责任，但应当减轻或免除处罚。",
        "relevance_score": 0.69,
        "source_path": "/data/books/law_fundamentals.pdf",
    },
    {
        "chunk_id": "stub-007",
        "book_title": "法学基础（示例书）",
        "page_num": 31,
        "chapter": "第一章 刑事诉讼原则",
        "content": "无罪推定原则：任何人在被法院依法判决有罪之前，应被推定为无罪。"
                   "该原则是现代刑事诉讼的基石，要求控方承担举证责任，疑罪从无。",
        "relevance_score": 0.65,
        "source_path": "/data/books/law_fundamentals.pdf",
    },
    {
        "chunk_id": "stub-008",
        "book_title": "深度学习（示例书）",
        "page_num": 156,
        "chapter": "第六章 优化算法",
        "content": "过拟合指模型在训练集上表现优异但在测试集上性能下降的现象。"
                   "常见对策：Dropout、L1/L2 正则化、数据增强、早停（Early Stopping）。",
        "relevance_score": 0.61,
        "source_path": "/data/books/deep_learning.pdf",
    },
    {
        "chunk_id": "stub-009",
        "book_title": "人工智能导论（示例书）",
        "page_num": 8,
        "chapter": "第一章 导言",
        "content": "人工智能（AI）是使计算机系统能够执行通常需要人类智能的任务的技术，"
                   "包括推理、学习、规划和理解自然语言。图灵在 1950 年提出图灵测试。",
        "relevance_score": 0.58,
        "source_path": "/data/books/ai_intro.pdf",
    },
    {
        "chunk_id": "stub-010",
        "book_title": "人工智能导论（示例书）",
        "page_num": 22,
        "chapter": "第一章 导言",
        "content": "反向传播算法（Backpropagation）通过链式法则计算损失函数对每个参数的梯度，"
                   "步骤：前向传播计算输出 → 计算损失 → 反向计算梯度 → 更新权重。",
        "relevance_score": 0.55,
        "source_path": "/data/books/ai_intro.pdf",
    },
]


# ── safe_calculate ────────────────────────────────────────────────────────────

_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd,
)


def _eval_ast(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Constant):
        try:
            return Decimal(str(node.value))
        except InvalidOperation as e:
            raise ValueError(f"无法转换为数值: {node.value}") from e
    if isinstance(node, ast.BinOp):
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("除以零")
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            if right == 0:
                raise ValueError("除以零")
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left ** right
    if isinstance(node, ast.UnaryOp):
        operand = _eval_ast(node.operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
    raise ValueError(f"不允许的操作节点: {type(node).__name__}")


def safe_calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression with Decimal precision.

    Raises ValueError for unsafe or invalid input.
    """
    expression = expression.strip()
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"表达式语法错误: {e}") from e

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"不允许的操作: {type(node).__name__}")

    result = _eval_ast(tree.body)
    # Remove trailing zeros for clean display
    normalized = result.normalize()
    # Decimal.normalize() uses E-notation for trailing-zero integers (e.g. 1E+3).
    # Convert those back to plain integer strings.
    sign, digits, exp = normalized.as_tuple()
    if exp > 0:
        normalized = normalized.quantize(Decimal(1))
    return str(normalized)


# ── ChunkResult ───────────────────────────────────────────────────────────────

@dataclasses.dataclass
class ChunkResult:
    chunk_id: str
    book_title: str
    page_num: int
    chapter: str
    content: str
    preview: str               # 截断文本，供前端缩略显示
    keyword_highlights: list[str]  # 命中关键词，供前端高亮
    relevance_score: float
    source_path: str           # 本地文件路径，供前端"查看详情"跳转


# ── ToolExecutor Protocol ─────────────────────────────────────────────────────

@runtime_checkable
class ToolExecutor(Protocol):
    def execute(self, name: str, args: dict) -> str:
        """Execute a tool and return result as string."""
        ...


# ── StubExecutor ──────────────────────────────────────────────────────────────

class StubExecutor:
    """Verification-phase executor.

    retrieve → returns up to max_results pre-defined ChunkResult objects as JSON.
    calculate → delegates to safe_calculate().

    In production (W3), replace with RealExecutor that hits ChromaDB + reranker.
    """

    def __init__(self, max_results: int = 10, preview_length: int = 200) -> None:
        self._max_results = max_results
        self._preview_length = preview_length

    def execute(self, name: str, args: dict) -> str:
        if name == "retrieve":
            return self._retrieve(args)
        if name == "calculate":
            return self._calculate(args)
        if name == "get_chunk":
            return self._get_chunk(args)
        raise ValueError(f"未知工具: {name}")

    def _retrieve(self, args: dict) -> str:
        query: str = args.get("query", "")
        k: int = min(int(args.get("k", 5)), self._max_results)

        keywords = [w for w in query.split() if len(w) > 1][:5]
        chunks = _STUB_CHUNKS[:k]

        results = []
        for raw in chunks:
            content: str = raw["content"]
            preview = content[: self._preview_length]
            results.append(
                dataclasses.asdict(
                    ChunkResult(
                        chunk_id=raw["chunk_id"],
                        book_title=raw["book_title"],
                        page_num=raw["page_num"],
                        chapter=raw["chapter"],
                        content=content,
                        preview=preview,
                        keyword_highlights=keywords,
                        relevance_score=raw["relevance_score"],
                        source_path=raw["source_path"],
                    )
                )
            )
        return json.dumps(results, ensure_ascii=False)

    def _calculate(self, args: dict) -> str:
        expression: str = args.get("expression", "")
        try:
            return safe_calculate(expression)
        except ValueError as e:
            return f"计算错误: {e}"

    def _get_chunk(self, args: dict) -> str:
        chunk_id: str = args.get("chunk_id", "")
        for raw in _STUB_CHUNKS:
            if raw["chunk_id"] == chunk_id:
                content: str = raw["content"]
                chunk = ChunkResult(
                    chunk_id=raw["chunk_id"],
                    book_title=raw["book_title"],
                    page_num=raw["page_num"],
                    chapter=raw["chapter"],
                    content=content,
                    preview=content[: self._preview_length],
                    keyword_highlights=[],
                    relevance_score=raw["relevance_score"],
                    source_path=raw["source_path"],
                )
                return json.dumps(dataclasses.asdict(chunk), ensure_ascii=False)
        return json.dumps({"error": f"未找到该 chunk: {chunk_id}"}, ensure_ascii=False)


# ── RealExecutor ──────────────────────────────────────────────────────────────

def _format_mmss(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


def _format_citation(
    source_file,
    page_start,
    page_end,
    start_sec,
    end_sec,
) -> str:
    if page_start is not None:
        if page_end is not None and page_end != page_start:
            return f"{source_file} p.{page_start}-{page_end}"
        return f"{source_file} p.{page_start}"
    if start_sec is not None and end_sec is not None:
        return f"{source_file} {_format_mmss(start_sec)}-{_format_mmss(end_sec)}"
    return source_file


def _to_record(raw: dict) -> dict:
    return {
        "chunk_id": raw["chunk_id"],
        "content": raw["content"],
        "element_type": raw.get("element_type"),
        "source_file": raw.get("source_file"),
        "citation": _format_citation(
            raw.get("source_file"),
            raw.get("page_start"),
            raw.get("page_end"),
            raw.get("start_sec"),
            raw.get("end_sec"),
        ),
        "low_confidence": raw.get("low_confidence", False),
        "score": raw.get("score"),
    }


class RealExecutor:
    """Production executor backed by real ChromaDB retrieval.

    retrieve → embeds the query with Embedder, queries ChromaStore for the fixed book_id.
    get_chunk → re-hydrates a single chunk's full content by id (multi-turn recall).
    calculate → delegates to safe_calculate() (same logic as StubExecutor).
    """

    def __init__(
        self,
        book_id: str,
        embedder: Embedder,
        store: ChromaStore,
        max_results: int = 10,
    ) -> None:
        self._book_id = book_id
        self._embedder = embedder
        self._store = store
        self._max_results = max_results

    def execute(self, name: str, args: dict) -> str:
        if name == "retrieve":
            return self._retrieve(args)
        if name == "calculate":
            return self._calculate(args)
        if name == "get_chunk":
            return self._get_chunk(args)
        raise ValueError(f"未知工具: {name}")

    def _retrieve(self, args: dict) -> str:
        query: str = args.get("query", "")
        k: int = min(int(args.get("k", 5)), self._max_results)
        vector = self._embedder.embed_query(query)
        raw_results = self._store.query(self._book_id, vector, n_results=k)
        records = [_to_record(r) for r in raw_results]
        return json.dumps(records, ensure_ascii=False)

    def _get_chunk(self, args: dict) -> str:
        chunk_id: str = args.get("chunk_id", "")
        raw_results = self._store.get(self._book_id, [chunk_id])
        if not raw_results:
            return json.dumps({"error": f"未找到该 chunk: {chunk_id}"}, ensure_ascii=False)
        return json.dumps(_to_record(raw_results[0]), ensure_ascii=False)

    def _calculate(self, args: dict) -> str:
        expression: str = args.get("expression", "")
        try:
            return safe_calculate(expression)
        except ValueError as e:
            return f"计算错误: {e}"
