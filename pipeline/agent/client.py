from __future__ import annotations

import dataclasses
import json
import time
from typing import Optional

import httpx
from openai import OpenAI

from pipeline.agent.executor import ToolExecutor
from pipeline.agent.tools import get_tools_param

_MAX_ROUNDS = 5  # 防止无限循环


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


class OllamaAgentClient:
    """Multi-turn tool-calling agent backed by an Ollama model.

    In verification (W1): pair with StubExecutor.
    In production (W3): pair with RealExecutor — no other changes needed.
    """

    _SYSTEM_PROMPT = (
        "你是一位严谨的学术助手，配有以下工具：\n"
        "- retrieve: 当需要查阅书中具体知识、公式、定义时调用\n"
        "- calculate: 当需要进行精确数值运算时调用（如乘除法、百分比、幂次）\n"
        "对于普通对话或无需查阅/计算的问题，直接回答，不调用任何工具。\n"
        "回答必须有据可查，检索不到相关内容时输出 [未找到参考资料]。"
    )

    def __init__(
        self,
        model: str,
        executor: ToolExecutor,
        base_url: str = "http://localhost:11434/v1",
        num_ctx: int = 8192,
        temperature: float = 0.0,
        keep_alive: int = 1200,
    ) -> None:
        self._model = model
        self._executor = executor
        self._num_ctx = num_ctx
        self._temperature = temperature
        self._keep_alive = keep_alive
        # trust_env=False 防止系统代理（如 socks://）干扰本地 Ollama 连接
        self._openai = OpenAI(
            base_url=base_url,
            api_key="ollama",
            http_client=httpx.Client(trust_env=False),
        )

    def run(self, question: str, system_prompt: str = "") -> AgentTurn:
        t0 = time.perf_counter()
        messages: list[dict] = [
            {"role": "system", "content": system_prompt or self._SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        triggered_tool: Optional[str] = None
        tool_args: Optional[dict] = None
        format_ok: bool = True
        total_tokens: int = 0
        prompt_tokens: int = 0
        completion_tokens: int = 0

        for _ in range(_MAX_ROUNDS):
            response = self._openai.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=get_tools_param(),
                temperature=self._temperature,
                extra_body={
                    "options": {"num_ctx": self._num_ctx},
                    "keep_alive": self._keep_alive,
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
                        final_answer="[TOOL_ARGS_PARSE_ERROR]",
                        total_tokens=total_tokens,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        latency_s=time.perf_counter() - t0,
                    )

                triggered_tool = tool_name
                tool_args = args

                # Append assistant message with tool_calls, then tool result
                messages.append(choice.message)
                result = self._executor.execute(tool_name, args)
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
                )

        # Max rounds exceeded
        return AgentTurn(
            question=question,
            triggered_tool=triggered_tool,
            tool_args=tool_args,
            format_ok=format_ok,
            fill_ok=None,
            final_answer="[MAX_ROUNDS_EXCEEDED]",
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_s=time.perf_counter() - t0,
        )
