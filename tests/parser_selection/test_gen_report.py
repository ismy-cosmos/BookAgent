import json
import csv
import pytest
from pathlib import Path


def _make_results(tmp_path: Path, parser: str, pages: list[dict]) -> None:
    d = tmp_path / parser
    d.mkdir(parents=True, exist_ok=True)
    for p in pages:
        (d / f"{p['id']}.json").write_text(json.dumps({
            "id": p["id"], "parser": parser,
            "elapsed_sec": p["elapsed_sec"],
            "char_count": p.get("char_count", 100),
            "elements": [], "error": p.get("error"),
        }))


def _make_scorecard(tmp_path: Path, rows: list[dict]) -> None:
    with open(tmp_path / "scorecard.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "parser", "element_type",
                                               "detect", "content", "struct", "notes"])
        writer.writeheader()
        writer.writerows(rows)


def _run_report(tmp_path: Path) -> str:
    from eval.parser_selection.scripts.gen_report import main
    main(results_dir=tmp_path, report_path=tmp_path / "report.md")
    return (tmp_path / "report.md").read_text()


def _15_pages(elapsed: float, parser: str) -> list[dict]:
    return [{"id": f"p{i:02d}", "elapsed_sec": elapsed} for i in range(15)]


def _15_scorecard_rows(detect: str, content: str, struct: str) -> list[dict]:
    rows = []
    for i in range(15):
        for p in ("unstructured", "marker"):
            rows.append({"id": f"p{i:02d}", "parser": p, "element_type": "x",
                         "detect": detect, "content": content, "struct": struct, "notes": ""})
    return rows


def test_report_contains_speed_table(tmp_path):
    _make_results(tmp_path, "unstructured", _15_pages(2.0, "unstructured"))
    _make_results(tmp_path, "marker", _15_pages(2.0, "marker"))
    _make_scorecard(tmp_path, _15_scorecard_rows("2", "2", "2"))
    report = _run_report(tmp_path)
    assert "pages/min" in report
    assert "unstructured" in report
    assert "marker" in report


def test_report_recommends_higher_scorer(tmp_path):
    _make_results(tmp_path, "unstructured", _15_pages(1.0, "unstructured"))  # 60 ppm — fast
    _make_results(tmp_path, "marker", _15_pages(1.5, "marker"))              # 40 ppm — fast
    rows = []
    for i in range(15):
        rows.append({"id": f"p{i:02d}", "parser": "unstructured", "element_type": "x",
                     "detect": "2", "content": "2", "struct": "2", "notes": ""})
        rows.append({"id": f"p{i:02d}", "parser": "marker", "element_type": "x",
                     "detect": "1", "content": "1", "struct": "1", "notes": ""})
    _make_scorecard(tmp_path, rows)
    report = _run_report(tmp_path)
    rec_section = report.split("选定：")[1]
    assert "unstructured" in rec_section


def test_report_disqualifies_slow_parser(tmp_path):
    _make_results(tmp_path, "unstructured", _15_pages(10.0, "unstructured"))  # 6 ppm — too slow
    _make_results(tmp_path, "marker", _15_pages(1.0, "marker"))               # 60 ppm — fast
    _make_scorecard(tmp_path, _15_scorecard_rows("2", "2", "2"))
    report = _run_report(tmp_path)
    rec_section = report.split("选定：")[1]
    assert "marker" in rec_section
