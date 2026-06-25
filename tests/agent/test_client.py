import json
import pytest
from unittest.mock import MagicMock, patch


# ── Test helpers ──────────────────────────────────────────────────────────────

def _make_tool_response(tool_name: str, tool_args_json: str, call_id: str = "call_abc123"):
    """Mock response where model requests a tool call."""
    func = MagicMock()
    func.name = tool_name
    func.arguments = tool_args_json
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function = func
    resp = MagicMock()
    resp.choices[0].finish_reason = "tool_calls"
    resp.choices[0].message.content = None
    resp.choices[0].message.tool_calls = [tool_call]
    resp.usage.total_tokens = 120
    return resp


def _make_text_response(content: str):
    """Mock response where model returns a final text answer."""
    resp = MagicMock()
    resp.choices[0].finish_reason = "stop"
    resp.choices[0].message.content = content
    resp.choices[0].message.tool_calls = None
    resp.usage.total_tokens = 60
    return resp


# ── Tests ─────────────────────────────────────────────────────────────────────

@patch("pipeline.agent.client.OpenAI")
def test_agent_turn_has_required_fields(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient, AgentTurn
    from pipeline.agent.executor import StubExecutor

    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_text_response("你好！我可以帮助你查阅书中知识。")
    )

    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("你好")

    assert isinstance(turn, AgentTurn)
    for field in ("question", "triggered_tool", "tool_args", "format_ok",
                  "fill_ok", "final_answer", "total_tokens", "latency_s"):
        assert hasattr(turn, field), f"AgentTurn missing field: {field}"


@patch("pipeline.agent.client.OpenAI")
def test_no_tool_call_returns_direct_answer(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_text_response("我是学术助手，可以帮你查书。")
    )

    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("你能做什么？")

    assert turn.triggered_tool is None
    assert turn.tool_args is None
    assert turn.format_ok is True
    assert "助手" in turn.final_answer


@patch("pipeline.agent.client.OpenAI")
def test_calculate_tool_call_executes_and_fills(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    mock_openai_cls.return_value.chat.completions.create.side_effect = [
        _make_tool_response("calculate", '{"expression": "0.5 * 70"}'),
        _make_text_response("用药量为 35 mg。"),
    ]

    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("患者体重 70kg，按 0.5mg/kg 计算用药量")

    assert turn.triggered_tool == "calculate"
    assert turn.tool_args == {"expression": "0.5 * 70"}
    assert turn.format_ok is True
    assert "35" in turn.final_answer


@patch("pipeline.agent.client.OpenAI")
def test_retrieve_tool_call_executes_and_fills(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    mock_openai_cls.return_value.chat.completions.create.side_effect = [
        _make_tool_response("retrieve", '{"query": "注意力机制公式", "k": 3}'),
        _make_text_response("注意力机制核心公式为 Attention(Q,K,V)=softmax(QK^T/√d_k)V。"),
    ]

    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("注意力机制的核心公式是什么？")

    assert turn.triggered_tool == "retrieve"
    assert turn.tool_args["query"] == "注意力机制公式"
    assert turn.format_ok is True
    assert turn.final_answer != ""


@patch("pipeline.agent.client.OpenAI")
def test_malformed_tool_args_sets_format_ok_false(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    # 模型返回格式错误的 JSON arguments
    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_tool_response("calculate", "{invalid json}")
    )

    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("计算 2 的 10 次方")

    assert turn.format_ok is False


@patch("pipeline.agent.client.OpenAI")
def test_fill_ok_is_none_for_manual_review(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_text_response("直接回答")
    )

    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("你好")

    assert turn.fill_ok is None  # 永远 None，人工复核


@patch("pipeline.agent.client.OpenAI")
def test_latency_and_tokens_are_recorded(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_text_response("回答")
    )

    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("问题")

    assert turn.latency_s >= 0
    assert turn.total_tokens >= 0
