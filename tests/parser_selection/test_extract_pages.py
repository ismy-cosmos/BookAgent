import json
import pytest
import pypdf
from pathlib import Path


def make_test_pdf(path: Path, num_pages: int = 3) -> Path:
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        writer.write(f)
    return path


def test_extracts_correct_page(tmp_path):
    from eval.parser_selection.scripts.extract_pages import extract_pages

    raw_dir = tmp_path / "raw" / "cs"
    raw_dir.mkdir(parents=True)
    make_test_pdf(raw_dir / "test.pdf", num_pages=3)

    config = [{"id": "t-01", "source": "cs/test.pdf", "page": 2,
               "element_type": "纯正文", "note": "test"}]
    config_path = tmp_path / "pages.json"
    config_path.write_text(json.dumps(config))
    out_dir = tmp_path / "pages"

    results = extract_pages(config_path, tmp_path / "raw", out_dir)

    assert results[0] == ("t-01", True, "extracted")
    out_pdf = out_dir / "t-01.pdf"
    assert out_pdf.exists()
    r = pypdf.PdfReader(str(out_pdf))
    assert len(r.pages) == 1


def test_missing_source_returns_error(tmp_path):
    from eval.parser_selection.scripts.extract_pages import extract_pages

    config = [{"id": "t-01", "source": "cs/missing.pdf", "page": 1,
               "element_type": "纯正文", "note": "test"}]
    config_path = tmp_path / "pages.json"
    config_path.write_text(json.dumps(config))

    results = extract_pages(config_path, tmp_path / "raw", tmp_path / "pages")

    assert results[0][1] is False
    assert "source missing" in results[0][2]


def test_idempotent_skips_existing(tmp_path):
    from eval.parser_selection.scripts.extract_pages import extract_pages

    raw_dir = tmp_path / "raw" / "cs"
    raw_dir.mkdir(parents=True)
    make_test_pdf(raw_dir / "test.pdf", num_pages=2)

    config = [{"id": "t-01", "source": "cs/test.pdf", "page": 1,
               "element_type": "纯正文", "note": "test"}]
    config_path = tmp_path / "pages.json"
    config_path.write_text(json.dumps(config))
    out_dir = tmp_path / "pages"

    extract_pages(config_path, tmp_path / "raw", out_dir)
    results = extract_pages(config_path, tmp_path / "raw", out_dir)

    assert results[0] == ("t-01", True, "skipped")
