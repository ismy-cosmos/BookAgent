from unittest.mock import MagicMock


def _fake_turn(final_answer="答案", triggered_tool=None, retrieved_chunks=None,
               total_tokens=10, latency_s=0.1):
    turn = MagicMock()
    turn.final_answer = final_answer
    turn.triggered_tool = triggered_tool
    turn.retrieved_chunks = retrieved_chunks or []
    turn.total_tokens = total_tokens
    turn.latency_s = latency_s
    return turn


def test_answer_returns_final_answer_text():
    from pipeline.agent.answer import answer
    client = MagicMock()
    client.run.return_value = _fake_turn(final_answer="这是答案")

    result = answer("问题", history=[], client=client)
    assert result.answer == "这是答案"


def test_answer_passes_history_to_client_run():
    from pipeline.agent.answer import answer
    from pipeline.agent.schema import ChatTurn

    client = MagicMock()
    client.run.return_value = _fake_turn()
    history = [ChatTurn(question="上一个问题", answer="上一个答案")]

    answer("新问题", history=history, client=client)
    client.run.assert_called_once_with("新问题", history=history)


def test_answer_appends_new_turn_to_returned_history():
    from pipeline.agent.answer import answer
    client = MagicMock()
    client.run.return_value = _fake_turn(final_answer="答案X")

    result = answer("问题X", history=[], client=client)
    assert len(result.history) == 1
    assert result.history[0].question == "问题X"
    assert result.history[0].answer == "答案X"


def test_answer_does_not_mutate_input_history():
    from pipeline.agent.answer import answer
    from pipeline.agent.schema import ChatTurn

    client = MagicMock()
    client.run.return_value = _fake_turn()
    original_history = [ChatTurn(question="q0", answer="a0")]

    answer("q1", history=original_history, client=client)
    assert len(original_history) == 1  # 原列表未被就地修改


def test_answer_maps_retrieved_chunks_to_citations():
    from pipeline.agent.answer import answer
    client = MagicMock()
    client.run.return_value = _fake_turn(retrieved_chunks=[{
        "chunk_id": "b/f/p0001/0000", "content": "内容", "element_type": "text",
        "source_file": "f.pdf", "citation": "f.pdf p.1", "low_confidence": False,
        "score": 0.1,
    }])

    result = answer("问题", history=[], client=client)
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "b/f/p0001/0000"
    assert result.citations[0].citation == "f.pdf p.1"
    assert result.history[0].citations[0].chunk_id == "b/f/p0001/0000"


def test_answer_empty_citations_when_no_retrieval():
    from pipeline.agent.answer import answer
    client = MagicMock()
    client.run.return_value = _fake_turn(retrieved_chunks=[])

    result = answer("问题", history=[], client=client)
    assert result.citations == []


def test_answer_result_has_all_fields():
    from pipeline.agent.answer import answer, AnswerResult
    client = MagicMock()
    client.run.return_value = _fake_turn(triggered_tool="retrieve", total_tokens=42, latency_s=0.5)

    result = answer("问题", history=[], client=client)
    assert isinstance(result, AnswerResult)
    assert result.triggered_tool == "retrieve"
    assert result.total_tokens == 42
    assert result.latency_s == 0.5