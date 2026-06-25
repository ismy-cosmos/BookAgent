from __future__ import annotations


def get_tools_param() -> list[dict]:
    """Return the OpenAI-compatible tools list for Ollama API calls."""
    return [
        {
            "type": "function",
            "function": {
                "name": "retrieve",
                "description": (
                    "从书籍知识库中检索与问题相关的段落。"
                    "当需要查阅书中的定义、公式、理论或具体内容时调用。"
                    "返回按相关度排序的 chunk 列表（JSON 数组）。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "用于检索的查询语句，应尽量具体",
                        },
                        "k": {
                            "type": "integer",
                            "description": "返回结果数量上限，默认 5，最大 10",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": (
                    "对数学表达式进行高精度求值。"
                    "当需要精确计算（如乘除法、百分比、幂次）时调用。"
                    "先用 retrieve 确认公式，再将具体数值代入表达式调用此工具。"
                    "expression 只能包含数字和四则运算符（+、-、*、/、//、%、**），"
                    "不允许函数调用或变量。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "合法的数学表达式，例如 '0.5 * 70' 或 '2 ** 10'",
                        },
                    },
                    "required": ["expression"],
                },
            },
        },
    ]
