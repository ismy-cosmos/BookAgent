from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from pipeline.agent.client import OllamaAgentClient
from pipeline.agent.schema import ChatTurn, Citation


@dataclass
class AnswerResult:
    answer: str
    history: list[ChatTurn]
    citations: list[Citation]
    triggered_tool: Optional[str]
    total_tokens: int
    latency_s: float


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

    chat_turn = ChatTurn(question=question, answer=turn.final_answer, citations=citations)
    new_history = history + [chat_turn]

    return AnswerResult(
        answer=turn.final_answer,
        history=new_history,
        citations=citations,
        triggered_tool=turn.triggered_tool,
        total_tokens=turn.total_tokens,
        latency_s=turn.latency_s,
    )