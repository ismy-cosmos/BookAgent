def test_new_names_importable_from_package():
    from pipeline.agent import RealExecutor, ChatTurn, Citation, AnswerResult, answer
    assert RealExecutor is not None
    assert ChatTurn is not None
    assert Citation is not None
    assert AnswerResult is not None
    assert callable(answer)


def test_existing_names_still_importable():
    from pipeline.agent import (
        ChunkResult, StubExecutor, ToolExecutor, safe_calculate,
        get_tools_param, AgentTurn, OllamaAgentClient,
    )
    assert ChunkResult is not None
    assert StubExecutor is not None