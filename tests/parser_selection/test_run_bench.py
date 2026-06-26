import json
import csv
import pytest
from pathlib import Path
from unittest.mock import patch


def _write_blank_pdf(path: Path) -> None:
    import pypdf
    path.parent.mkdir(parents=True, exist_ok=True)
    w = pypdf.PdfWriter()
    w.add_blank_page(612, 792)
    with open(path, "wb") as f:
        w.write(f)


# ── bench_page ────────────────────────────────────────────────────────────────

def test_bench_page_success(tmp_path):
    from eval.parser_selection.scripts.run_bench import bench_page

    pdf = tmp_path / "cs-01.pdf"
    _write_blank_pdf(pdf)
    mock_el = {"type": "text", "content": "hello world", "page_num": 1}

    with patch("eval.parser_selection.scripts.run_bench.run_unstructured",
               return_value=([mock_el], 0.5)), \
         patch("eval.parser_selection.scripts.run_bench.run_marker",
               return_value=([mock_el], 0.8)):
        result = bench_page("cs-01", str(pdf))

    assert result["id"] == "cs-01"
    assert result["unstructured"]["elapsed_sec"] == pytest.approx(0.5, abs=0.01)
    assert result["unstructured"]["error"] is None
    assert result["unstructured"]["char_count"] == len("hello world")
    assert result["marker"]["elapsed_sec"] == pytest.approx(0.8, abs=0.01)


def test_bench_page_parser_error(tmp_path):
    from eval.parser_selection.scripts.run_bench import bench_page

    pdf = tmp_path / "cs-01.pdf"
    _write_blank_pdf(pdf)

    def boom(_path):
        raise RuntimeError("parse failed")

    with patch("eval.parser_selection.scripts.run_bench.run_unstructured", side_effect=boom), \
         patch("eval.parser_selection.scripts.run_bench.run_marker",
               return_value=([], 0.1)):
        result = bench_page("cs-01", str(pdf))

    assert result["unstructured"]["error"] is not None
    assert "parse failed" in result["unstructured"]["error"]
    assert result["marker"]["error"] is None


# ── write_scorecard_skeleton ──────────────────────────────────────────────────

def test_scorecard_skeleton_structure(tmp_path):
    from eval.parser_selection.scripts.run_bench import write_scorecard_skeleton

    config = [
        {"id": "cs-01", "element_type": "纯正文"},
        {"id": "cs-02", "element_type": "代码块"},
    ]
    write_scorecard_skeleton(config, tmp_path)

    rows = list(csv.DictReader(open(tmp_path / "scorecard.csv")))
    assert len(rows) == 4  # 2 pages × 2 parsers
    assert {r["parser"] for r in rows} == {"unstructured", "marker"}
    assert all(r["detect"] == "" for r in rows)
    assert all(r["content"] == "" for r in rows)
    assert all(r["struct"] == "" for r in rows)


def test_scorecard_skeleton_idempotent(tmp_path):
    from eval.parser_selection.scripts.run_bench import write_scorecard_skeleton

    config = [{"id": "cs-01", "element_type": "纯正文"}]
    write_scorecard_skeleton(config, tmp_path)
    mtime1 = (tmp_path / "scorecard.csv").stat().st_mtime
    write_scorecard_skeleton(config, tmp_path)
    mtime2 = (tmp_path / "scorecard.csv").stat().st_mtime
    assert mtime1 == mtime2


# ── write_results ─────────────────────────────────────────────────────────────

def test_write_results_creates_json(tmp_path):
    from eval.parser_selection.scripts.run_bench import write_results

    result = {
        "id": "cs-01",
        "unstructured": {"elapsed_sec": 0.5, "char_count": 10,
                         "elements": [], "error": None},
        "marker":        {"elapsed_sec": 0.8, "char_count": 12,
                         "elements": [], "error": None},
    }
    write_results(result, tmp_path)

    for parser in ("unstructured", "marker"):
        out = tmp_path / parser / "cs-01.json"
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["id"] == "cs-01"
        assert data["parser"] == parser
