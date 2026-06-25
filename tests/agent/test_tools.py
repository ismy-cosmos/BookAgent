def test_get_tools_param_returns_list_of_two():
    from pipeline.agent.tools import get_tools_param
    tools = get_tools_param()
    assert isinstance(tools, list)
    assert len(tools) == 2


def test_each_tool_has_openai_structure():
    from pipeline.agent.tools import get_tools_param
    for tool in get_tools_param():
        assert tool["type"] == "function"
        assert "function" in tool
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert fn["parameters"]["type"] == "object"
        assert "properties" in fn["parameters"]


def test_retrieve_tool_has_query_and_k():
    from pipeline.agent.tools import get_tools_param
    retrieve = next(t for t in get_tools_param() if t["function"]["name"] == "retrieve")
    props = retrieve["function"]["parameters"]["properties"]
    assert "query" in props
    assert "k" in props
    assert retrieve["function"]["parameters"].get("required") == ["query"]


def test_calculate_tool_has_expression():
    from pipeline.agent.tools import get_tools_param
    calculate = next(t for t in get_tools_param() if t["function"]["name"] == "calculate")
    props = calculate["function"]["parameters"]["properties"]
    assert "expression" in props
    assert calculate["function"]["parameters"].get("required") == ["expression"]


def test_tools_names_are_retrieve_and_calculate():
    from pipeline.agent.tools import get_tools_param
    names = {t["function"]["name"] for t in get_tools_param()}
    assert names == {"retrieve", "calculate"}
