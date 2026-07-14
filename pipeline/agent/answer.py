from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from pipeline.agent.client import (
    CITATION_TAG_PREFIX,
    MAX_ROUNDS_EXCEEDED,
    NO_CITATION_TAG,
    TOOL_ARGS_PARSE_ERROR,
    USED_CALCULATE_TAG,
    OllamaAgentClient,
)
from pipeline.agent.schema import ChatTurn, Citation

_ERROR_SENTINELS = (TOOL_ARGS_PARSE_ERROR, MAX_ROUNDS_EXCEEDED)


def _citation_tag(citations: list[Citation]) -> str:
    handles = "；".join(c.citation for c in citations)
    return f"{CITATION_TAG_PREFIX}{handles}]"


def _append_tool_tags(text: str, citations: list[Citation], used_calculate: bool) -> str:
    """按这一轮真实用没用过 retrieve/calculate 拼标记，不信模型自己写的。"""
    tags = [_citation_tag(citations) if citations else NO_CITATION_TAG]
    if used_calculate:
        tags.append(USED_CALCULATE_TAG)
    return text + "\n" + "\n".join(tags)


@dataclass
class AnswerResult:
    answer: str
    history: list[ChatTurn]
    citations: list[Citation]
    triggered_tool: Optional[str]
    total_tokens: int
    latency_s: float
    used_calculate: bool
    attempted_retrieve: bool


def answer(
    question: str,
    history: list[ChatTurn],
    client: OllamaAgentClient,
) -> AnswerResult:
    """无状态问答入口：跑一轮多轮 agent，把本轮 retrieve 命中映射为 citations，追加进历史返回。"""
    turn = client.run(question, history=history)

    citations = [
        Citation(
            chunk_id=record.get("chunk_id", ""),
            source_file=record.get("source_file") or "",
            element_type=record.get("element_type") or "",
            citation=record.get("citation", ""),
            score=record.get("score"),
        )
        for record in turn.retrieved_chunks
    ]

    final_answer = turn.final_answer
    if final_answer not in _ERROR_SENTINELS:
        final_answer = _append_tool_tags(final_answer, citations, turn.used_calculate)

    chat_turn = ChatTurn(
        question=question, answer=final_answer, citations=citations,
        used_calculate=turn.used_calculate, attempted_retrieve=turn.attempted_retrieve,
    )
    new_history = history + [chat_turn]

    return AnswerResult(
        answer=final_answer,
        history=new_history,
        citations=citations,
        triggered_tool=turn.triggered_tool,
        total_tokens=turn.total_tokens,
        latency_s=turn.latency_s,
        used_calculate=turn.used_calculate,
        attempted_retrieve=turn.attempted_retrieve,
    )