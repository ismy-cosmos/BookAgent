from .base import Element, Parser


class MarkerParser(Parser):
    """Marker-pdf adapter — implement after parser selection benchmark."""

    def parse(self, pdf_path: str) -> list[Element]:
        raise NotImplementedError(
            "MarkerParser not yet implemented; "
            "run the parser selection benchmark first."
        )
