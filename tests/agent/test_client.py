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
    resp.usage.prompt_tokens = 90
    resp.usage.completion_tokens = 30
    return resp


def _make_text_response(content: str):
    """Mock response where model returns a final text answer."""
    resp = MagicMock()
    resp.choices[0].finish_reason = "stop"
    resp.choices[0].message.content = content
    resp.choices[0].message.tool_calls = None
    resp.usage.total_tokens = 60
    resp.usage.prompt_tokens = 40
    resp.usage.completion_tokens = 20
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


@patch("pipeline.agent.client.OpenAI")
def test_keep_alive_default_is_1200(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor
    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    assert client._keep_alive == 1200


@patch("pipeline.agent.client.OpenAI")
def test_extra_body_passes_num_ctx_and_keep_alive(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor
    mock_create = mock_openai_cls.return_value.chat.completions.create
    mock_create.return_value = _make_text_response("ok")
    client = OllamaAgentClient(model="test-model", executor=StubExecutor(),
                               num_ctx=4096, keep_alive=600)
    client.run("question")
    kwargs = mock_create.call_args[1]
    assert kwargs["extra_body"]["options"]["num_ctx"] == 4096
    assert kwargs["extra_body"]["keep_alive"] == 600


@patch("pipeline.agent.client.OpenAI")
def test_history_replayed_as_user_assistant_pairs(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor
    from pipeline.agent.schema import ChatTurn

    mock_create = mock_openai_cls.return_value.chat.completions.create
    mock_create.return_value = _make_text_response("第二轮回答")

    history = [ChatTurn(question="第一轮问题", answer="第一轮回答")]
    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    client.run("第二轮问题", history=history)

    messages = mock_create.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "第一轮问题"}
    assert messages[2] == {"role": "assistant", "content": "第一轮回答"}
    assert messages[3] == {"role": "user", "content": "第二轮问题"}


@patch("pipeline.agent.client.OpenAI")
def test_history_replay_includes_compact_handle_list(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor
    from pipeline.agent.schema import ChatTurn, Citation

    mock_create = mock_openai_cls.return_value.chat.completions.create
    mock_create.return_value = _make_text_response("好的")

    citation = Citation(chunk_id="b/f/p0001/0000", source_file="f.pdf",
                         element_type="text", citation="f.pdf p.1", score=0.1)
    history = [ChatTurn(question="问题", answer="答案", citations=[citation])]
    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    client.run("追问", history=history)

    messages = mock_create.call_args.kwargs["messages"]
    # citation 句柄必须放在独立的 system 消息里，不能粘在 assistant 的原话
    # 后面——不然模型容易把这段拼接文本误当成自己该输出的格式抄一遍
    # （复现过：同一问题在同一对话里问第二遍时，模型会把这段文本原样
    # 抄进新回答，即使这轮根本没有真实检索）。
    assert messages[2] == {"role": "assistant", "content": "答案"}
    handle_message = messages[3]["content"]
    assert messages[3]["role"] == "system"
    assert "f.pdf p.1" in handle_message
    assert "chunk_id=b/f/p0001/0000" in handle_message


@patch("pipeline.agent.client.OpenAI")
def test_history_replay_strips_deterministic_tags_from_answer(mock_openai_cls):
    """turn.answer 落盘时已经被 answer.py 拼上了强制标记（见 pipeline/agent/answer.py）。
    回放历史时必须把这些标记条剥掉，不然模型会看到自己"说过"的标记文本，
    在没有真实检索/计算的新一轮里原样抄一遍（复现过：同一问题问第二遍）。"""
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor
    from pipeline.agent.schema import ChatTurn, Citation

    mock_create = mock_openai_cls.return_value.chat.completions.create
    mock_create.return_value = _make_text_response("好的")

    citation = Citation(chunk_id="b/f/p0001/0000", source_file="f.pdf",
                         element_type="text", citation="f.pdf p.1", score=0.1)
    history = [ChatTurn(
        question="问题",
        answer="答案正文\n[引用来源：f.pdf p.1]",
        citations=[citation],
    )]
    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    client.run("追问", history=history)

    messages = mock_create.call_args.kwargs["messages"]
    assert messages[2] == {"role": "assistant", "content": "答案正文"}


@patch("pipeline.agent.client.OpenAI")
def test_history_replay_strips_no_citation_and_calculate_tags(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor
    from pipeline.agent.schema import ChatTurn

    mock_create = mock_openai_cls.return_value.chat.completions.create
    mock_create.return_value = _make_text_response("好的")

    history = [ChatTurn(
        question="1+1等于几",
        answer="等于2\n[未找到参考资料]\n[已使用计算工具]",
    )]
    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    client.run("追问", history=history)

    messages = mock_create.call_args.kwargs["messages"]
    assert messages[2] == {"role": "assistant", "content": "等于2"}


@patch("pipeline.agent.client.OpenAI")
def test_no_history_behaves_like_before(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    mock_create = mock_openai_cls.return_value.chat.completions.create
    mock_create.return_value = _make_text_response("答案")

    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    client.run("问题")

    messages = mock_create.call_args.kwargs["messages"]
    assert len(messages) == 2  # system + user，无历史插入
    assert messages[1] == {"role": "user", "content": "问题"}


@patch("pipeline.agent.client.OpenAI")
def test_retrieved_chunks_captured_on_retrieve_call(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import RealExecutor

    class _FakeEmbedder:
        def embed_query(self, text):
            return [0.1] * 4

    class _FakeStore:
        def query(self, book_id, vector, n_results=5):
            return [{
                "chunk_id": "b/f/p0001/0000", "content": "内容", "score": 0.1,
                "source_file": "f.pdf", "element_type": "text",
                "page_start": 1, "page_end": 1, "start_sec": None, "end_sec": None,
                "low_confidence": False,
            }]

    mock_openai_cls.return_value.chat.completions.create.side_effect = [
        _make_tool_response("retrieve", '{"query": "测试", "k": 3}'),
        _make_text_response("答案"),
    ]

    executor = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=_FakeStore())
    client = OllamaAgentClient(model="test-model", executor=executor)
    turn = client.run("问题")

    assert len(turn.retrieved_chunks) == 1
    assert turn.retrieved_chunks[0]["chunk_id"] == "b/f/p0001/0000"


@patch("pipeline.agent.client.OpenAI")
def test_retrieved_chunks_empty_when_no_retrieve_call(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_text_response("直接回答")
    )
    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("你好")
    assert turn.retrieved_chunks == []


@patch("pipeline.agent.client.OpenAI")
def test_agent_turn_has_token_split(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor
    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_text_response("答案")
    )
    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("问题")
    assert turn.prompt_tokens == 40
    assert turn.completion_tokens == 20
    assert turn.total_tokens == 60


@patch("pipeline.agent.client.OpenAI")
def test_attempted_retrieve_true_even_when_retrieve_returns_no_chunks(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import RealExecutor

    class _FakeEmbedder:
        def embed_query(self, text):
            return [0.1] * 4

    class _EmptyStore:
        def query(self, book_id, vector, n_results=5):
            return []

    mock_openai_cls.return_value.chat.completions.create.side_effect = [
        _make_tool_response("retrieve", '{"query": "测试", "k": 3}'),
        _make_text_response("答案"),
    ]

    executor = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=_EmptyStore())
    client = OllamaAgentClient(model="test-model", executor=executor)
    turn = client.run("问题")

    # 调用过 retrieve 但没查到内容，跟"压根没调用 retrieve"要能区分开——
    # 前者是"书里真没有"，后者是"这轮没查"，两种在 UI 上文案不一样。
    assert turn.attempted_retrieve is True
    assert turn.retrieved_chunks == []


@patch("pipeline.agent.client.OpenAI")
def test_attempted_retrieve_false_when_no_retrieve_call(mock_openai_cls):
    from pipeline.agent.client import OllamaAgentClient
    from pipeline.agent.executor import StubExecutor

    mock_openai_cls.return_value.chat.completions.create.return_value = (
        _make_text_response("直接回答")
    )
    client = OllamaAgentClient(model="test-model", executor=StubExecutor())
    turn = client.run("你好")
    assert turn.attempted_retrieve is False
