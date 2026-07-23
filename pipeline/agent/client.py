from __future__ import annotations

import dataclasses
import json
import time
from typing import Optional

import httpx
from openai import OpenAI

from pipeline.agent.executor import ToolExecutor
from pipeline.agent.schema import ChatTurn
from pipeline.agent.tools import get_tools_param

_MAX_ROUNDS = 5  # 防止无限循环

TOOL_ARGS_PARSE_ERROR = "[TOOL_ARGS_PARSE_ERROR]"
MAX_ROUNDS_EXCEEDED = "[MAX_ROUNDS_EXCEEDED]"

# 由 pipeline/agent/answer.py 按真实工具调用强制拼在答案末尾的标记——
# 回放历史时必须剥掉（见 _strip_known_tags），不然模型会把自己"说过"的
# 标记文本原样抄进没有真实检索/计算的新一轮。
NO_CITATION_TAG = "[未找到参考资料]"
USED_CALCULATE_TAG = "[已使用计算工具]"
CITATION_TAG_PREFIX = "[引用来源："


@dataclasses.dataclass
class AgentTurn:
    question: str
    triggered_tool: Optional[str]       # 触发的工具名，None 表示未触发
    tool_args: Optional[dict]           # 工具参数
    format_ok: bool                     # tool_call JSON 可被解析
    fill_ok: Optional[bool]             # 回填质量（None = 人工复核）
    final_answer: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    latency_s: float
    retrieved_chunks: list = dataclasses.field(default_factory=list)  # 本轮 retrieve 命中的记录（RealExecutor honest 形状）
    used_calculate: bool = False        # 本轮是否调用过 calculate
    attempted_retrieve: bool = False    # 本轮是否调用过 retrieve（不管有没有查到内容）


def _strip_known_tags(text: str) -> str:
    """去掉 answer.py 强制拼在末尾的标记行，只留模型自己的原话。"""
    lines = text.split("\n")
    while lines and (
        lines[-1] == NO_CITATION_TAG
        or lines[-1] == USED_CALCULATE_TAG
        or lines[-1].startswith(CITATION_TAG_PREFIX)
    ):
        lines.pop()
    return "\n".join(lines)


def _format_turn_for_replay(turn: ChatTurn) -> list[dict]:
    """把一个历史轮次压成回放给模型的消息列表。

    citation 句柄单独放进一条 system 消息，不粘在 assistant 的原话后面——
    粘在一起时模型容易把这段拼接格式误当成自己该输出的东西，在没有真实
    检索的新一轮里原样抄一遍（复现：同一问题在同一对话里问第二遍）。回放
    的 assistant 内容本身也要先剥掉强制拼上的标记行，理由相同。
    """
    messages = [{"role": "assistant", "content": _strip_known_tags(turn.answer)}]
    if turn.citations:
        handles = "；".join(f"{c.citation}(chunk_id={c.chunk_id})" for c in turn.citations)
        messages.append({
            "role": "system",
            "content": f"（你上一轮 retrieve 到的原文出处：{handles}；"
                       f"需要回看原文用 get_chunk 取对应 chunk_id 即可）",
        })
    return messages


class OllamaAgentClient:
    """Multi-turn tool-calling agent backed by an Ollama model.

    In verification (W1): pair with StubExecutor.
    In production (W3): pair with RealExecutor — no other changes needed.
    """

    _SYSTEM_PROMPT = (
        "你是一位严谨的学术助手，配有以下工具：\n"
        "- retrieve: 只要问题涉及书中内容、任何具体知识点/公式/定义，或者有可能需要查证，"
        "就必须调用，不要凭自己的知识直接回答；用户只要是在主动问书里的内容，"
        "就一定要调用，哪怕你觉得自己已经知道答案\n"
        "你对retrieve能查到的知识库里具体收录了什么内容、覆盖多大范围——没有任何先验信息"
        "（没有书名、目录、简介），不能仅凭问题读起来像“通用常识/常见法律法条问题”就判断"
        "这跟知识库无关而跳过检索，唯一能确认的办法是先调用retrieve看检索结果里有没有"
        "相关内容。\n"
        "retrieve返回的内容如果实际上没有回答问题（比如问A却查到了讲B的内容），"
        "要在回答里说明未查找到相关资料。\n"
        "- calculate: 只要问题涉及任何数值计算，哪怕只是很简单的加减乘除，都必须调用，"
        "不要自己心算\n"
        "- get_chunk: 当需要回看之前 retrieve 结果或对话历史中出现过的某个具体 chunk 原文时，"
        "用其 chunk_id 直接取回；探索新话题仍应使用 retrieve\n"
        "题目既涉及数值计算、又提到书中的场景/公式/术语时，正确顺序是先 retrieve 查证书里的"
        "表述和公式约定，再用查到的数字/公式调用 calculate，最后综合两者作答——不是先自己心算"
        "出数字再考虑要不要查。例如问题是"
        "“三个任务A(5ms)/B(10ms)/C(15ms)按FIFO调度，平均周转时间是多少”，"
        "“FIFO调度”“周转时间”是书里的术语，正确流程是先调用 retrieve 查这两个概念在书中的"
        "定义和计算公式，再调用 calculate 代入数字算出结果，不能跳过 retrieve 直接算。\n"
        "只有纯打招呼、寒暄这类跟书本内容和计算完全无关的对话，才可以不调用任何工具直接回答；"
        "拿不准该不该调用时，优先调用 retrieve。\n"
        "禁止自己编造任何形如 [xxx] 的引用/来源/未找到参考资料/计算工具标记——"
        "系统会在你回答之后，根据你这一轮有没有真的调用 retrieve、有没有真的"
        "调用 calculate，自动附加准确的标记，你自己写的不算数、也不需要写。"
    )

    def __init__(
        self,
        model: str,
        executor: ToolExecutor,
        base_url: str = "http://localhost:11434/v1",
        num_ctx: Optional[int] = None,  # None = 走模型默认（Modelfile num_ctx）；仅诊断时显式覆盖
        temperature: float = 0.0,
    ) -> None:
        self._model = model
        self._executor = executor
        self._num_ctx = num_ctx
        self._temperature = temperature
        # trust_env=False 防止系统代理（如 socks://）干扰本地 Ollama 连接
        self._openai = OpenAI(
            base_url=base_url,
            api_key="ollama",
            http_client=httpx.Client(trust_env=False),
        )

    def run(
        self,
        question: str,
        history: Optional[list[ChatTurn]] = None,
        system_prompt: str = "",
    ) -> AgentTurn:
        t0 = time.perf_counter()
        messages: list[dict] = [
            {"role": "system", "content": system_prompt or self._SYSTEM_PROMPT},
        ]
        for turn in history or []:
            messages.append({"role": "user", "content": turn.question})
            messages.extend(_format_turn_for_replay(turn))
        messages.append({"role": "user", "content": question})

        triggered_tool: Optional[str] = None
        tool_args: Optional[dict] = None
        format_ok: bool = True
        total_tokens: int = 0
        prompt_tokens: int = 0
        completion_tokens: int = 0
        retrieved_chunks: list = []
        used_calculate = False
        attempted_retrieve = False

        for _ in range(_MAX_ROUNDS):
            response = self._openai.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=get_tools_param(),
                temperature=self._temperature,
                # keep_alive 故意不传：Ollama /v1/chat/completions（OpenAI 兼容接口）
                # 不支持这个 Ollama 私有扩展字段，实测无论传什么值都静默回退到服务端
                # 默认 5 分钟（只有原生 /api/chat 才认）。
                extra_body={
                    "options": {} if self._num_ctx is None else {"num_ctx": self._num_ctx},
                },
            )

            if response.usage:
                total_tokens += response.usage.total_tokens
                prompt_tokens += getattr(response.usage, "prompt_tokens", 0) or 0
                completion_tokens += getattr(response.usage, "completion_tokens", 0) or 0

            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                tool_name = tool_call.function.name

                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    format_ok = False
                    # Can't proceed without valid args; return early
                    return AgentTurn(
                        question=question,
                        triggered_tool=tool_name,
                        tool_args=None,
                        format_ok=False,
                        fill_ok=None,
                        final_answer=TOOL_ARGS_PARSE_ERROR,
                        total_tokens=total_tokens,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        latency_s=time.perf_counter() - t0,
                        retrieved_chunks=retrieved_chunks,
                        used_calculate=used_calculate,
                        attempted_retrieve=attempted_retrieve,
                    )

                triggered_tool = tool_name
                tool_args = args

                # Append assistant message with tool_calls, then tool result
                messages.append(choice.message)
                result = self._executor.execute(tool_name, args)
                if tool_name == "retrieve":
                    attempted_retrieve = True
                    try:
                        parsed = json.loads(result)
                        if isinstance(parsed, list):
                            retrieved_chunks.extend(parsed)
                    except json.JSONDecodeError:
                        pass
                elif tool_name == "calculate":
                    used_calculate = True
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            else:
                # Final text answer
                final_answer = (choice.message.content or "").strip()
                return AgentTurn(
                    question=question,
                    triggered_tool=triggered_tool,
                    tool_args=tool_args,
                    format_ok=format_ok,
                    fill_ok=None,
                    final_answer=final_answer,
                    total_tokens=total_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_s=time.perf_counter() - t0,
                    retrieved_chunks=retrieved_chunks,
                    used_calculate=used_calculate,
                    attempted_retrieve=attempted_retrieve,
                )

        # Max rounds exceeded
        return AgentTurn(
            question=question,
            triggered_tool=triggered_tool,
            tool_args=tool_args,
            format_ok=format_ok,
            fill_ok=None,
            final_answer=MAX_ROUNDS_EXCEEDED,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_s=time.perf_counter() - t0,
            retrieved_chunks=retrieved_chunks,
            used_calculate=used_calculate,
            attempted_retrieve=attempted_retrieve,
        )
