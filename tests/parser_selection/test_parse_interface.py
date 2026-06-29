import pytest
from pipeline.parse import Element, Parser
from pipeline.parse.unstructured import UnstructuredParser


def test_element_default_metadata():
    e = Element(type="text", content="hello", page_num=1)
    assert e.metadata == {}


def test_element_with_metadata():
    e = Element(type="figure", content="", page_num=3,
                metadata={"caption": "Fig 1", "confidence": 0.9})
    assert e.metadata["caption"] == "Fig 1"
    assert e.page_num == 3


def test_parser_abstract_cannot_instantiate():
    with pytest.raises(TypeError):
        Parser()


def test_parser_concrete_subclass_works():
    class EchoParser(Parser):
        def parse(self, pdf_path: str) -> list[Element]:
            return [Element(type="text", content=pdf_path, page_num=1)]

    result = EchoParser().parse("test.pdf")
    assert len(result) == 1
    assert result[0].content == "test.pdf"
    assert result[0].type == "text"


def test_unstructured_parser_stub_raises():
    with pytest.raises(NotImplementedError):
        UnstructuredParser().parse("any.pdf")
