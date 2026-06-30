"""Live integration test for MarkerParser — runs the REAL marker-pdf
PdfConverter (loads actual ML model weights) against a real PDF.

Unlike test_marker_parser.py (fully mocked, fast), this test exists
specifically to catch drift between our assumptions about marker-pdf's
behavior (e.g. the page_separator it emits under paginate_output=True)
and what the installed marker-pdf version actually does. A fully-mocked
test suite can stay green forever while the real library silently changes
underneath it; this test is the guard against that.

Slow: loads marker's layout/OCR models. Requires the eval/testset/cs raw
PDFs to be present on disk.
"""
import os

import pytest

from pipeline.parse.marker import MarkerParser

_PDF_PATH = "eval/testset/cs/raw/book/cpu-intro.pdf"


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_marker_parser_real_pdf_no_page_zero():
    elements = MarkerParser().parse(_PDF_PATH)

    assert elements, "real PDF must produce elements"
    zero_page = [e for e in elements if e.page_num == 0]
    assert not zero_page, (
        f"{len(zero_page)} elements got page_num=0 — the page_separator "
        "MarkerParser derived from the live renderer did not match what "
        "the markdown actually contains"
    )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_marker_parser_real_pdf_page_count_matches_converter():
    converter = MarkerParser._get_converter()
    elements = MarkerParser().parse(_PDF_PATH)

    rendered = converter(_PDF_PATH)
    real_page_count = len(rendered.markdown.split(MarkerParser._page_sep)) - 1

    max_page_num = max(e.page_num for e in elements)
    assert max_page_num == real_page_count, (
        f"derived page_sep produced {max_page_num} pages from parse(), but "
        f"splitting the live converter's own output gives {real_page_count} — "
        "our separator assumption has drifted from the real renderer"
    )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_marker_parser_page_sep_is_derived_not_hardcoded():
    """MarkerParser._page_sep must come from the live renderer instance,
    not a guess baked into our source code."""
    MarkerParser._get_converter()
    resolved = MarkerParser._converter.resolve_dependencies(MarkerParser._converter.renderer)
    assert MarkerParser._page_sep == resolved.page_separator
