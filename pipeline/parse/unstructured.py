from .base import Element, Parser


class UnstructuredParser(Parser):
    """Unstructured adapter — implement after parser selection benchmark."""

    def parse(self, pdf_path: str) -> list[Element]:
        raise NotImplementedError(
            "UnstructuredParser not yet implemented; "
            "run the parser selection benchmark first."
        )
