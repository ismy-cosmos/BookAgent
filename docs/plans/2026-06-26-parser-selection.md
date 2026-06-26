# Parser Selection Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run Unstructured vs Marker-pdf on 15 representative single-page PDFs, collect timing + structured output, enable human scoring via CSV, generate a selection recommendation report, and scaffold the `pipeline/parse/` abstract interface.

**Architecture:** Four-stage pipeline — (1) `pages.json` config drives `extract_pages.py` to produce 15 single-page PDFs; (2) `run_bench.py` calls both parsers and writes per-page JSON + scorecard skeleton; (3) human fills `scorecard.csv`; (4) `gen_report.py` combines auto-metrics + scores into `report.md`. Parallel to this, `pipeline/parse/base.py` defines the stable `Element`/`Parser` interface; adapters are stubs pending selection.

**Tech Stack:** `pypdf` (extraction), `unstructured[pdf]` (parser A), `marker-pdf` (parser B), `pytest`, standard library (`json`, `csv`, `time`, `pathlib`).

## Global Constraints

- Python 3.12, venv `bookagent.venv` — activate before every command: `source bookagent.venv/bin/activate`
- Branch `feat/w1-parser-selection` — all commits go here
- Source PDFs live in `eval/parser_selection/fixtures/raw/` (gitignored; must be present locally before Task 2)
- Speed target: ≥ 15 pages/min to qualify; both parsers tested identically
- `pypdf` is already declared in `requirements.txt`; both parsers installed via `requirements-bench.txt` (not promoted to `requirements.txt` until winner decided)
- Run all tests from repo root: `pytest tests/ -v`

---

## File Map

| Path | Action | Responsibility |
|---|---|---|
| `eval/parser_selection/scripts/pages.json` | Create | 15-page configuration (source file + page number + element type) |
| `eval/parser_selection/scripts/extract_pages.py` | Create | Reads `pages.json`, extracts single-page PDFs into `fixtures/pages/` |
| `eval/parser_selection/scripts/run_bench.py` | Create | Calls both parsers per page, writes JSON results, generates scorecard skeleton |
| `eval/parser_selection/scripts/gen_report.py` | Create | Reads results + scorecard, writes `results/report.md` |
| `requirements-bench.txt` | Create | Pinned `unstructured[pdf]` + `marker-pdf` for benchmark only |
| `pipeline/parse/__init__.py` | Create | Re-exports `Element`, `Parser` |
| `pipeline/parse/base.py` | Create | `Element` dataclass + `Parser` ABC |
| `pipeline/parse/unstructured.py` | Create | Stub adapter (raises `NotImplementedError`) |
| `pipeline/parse/marker.py` | Create | Stub adapter (raises `NotImplementedError`) |
| `tests/parser_selection/__init__.py` | Create | Package marker |
| `tests/parser_selection/test_extract_pages.py` | Create | Tests for extraction logic |
| `tests/parser_selection/test_run_bench.py` | Create | Tests for bench result structure (parsers mocked) |
| `tests/parser_selection/test_gen_report.py` | Create | Tests for report generation (fixtures with mock data) |
| `tests/parser_selection/test_parse_interface.py` | Create | Tests for `Element` + `Parser` ABC |

---

### Task 1: pages.json + extract_pages.py

**Files:**
- Create: `eval/parser_selection/scripts/pages.json`
- Create: `eval/parser_selection/scripts/extract_pages.py`
- Create: `tests/parser_selection/__init__.py`
- Create: `tests/parser_selection/test_extract_pages.py`

**Interfaces:**
- Produces: `extract_pages(config_path, raw_dir, out_dir) -> list[tuple[str, bool, str]]` — list of `(id, success, message)`
- Produces: `fixtures/pages/<id>.pdf` for each entry in `pages.json`
- Consumed by: Task 2 (`run_bench.py` reads from `fixtures/pages/`)

- [ ] **Step 1: Create pages.json**

```
eval/parser_selection/scripts/pages.json
```

```json
[
  {"id": "cs-01", "source": "cs/cpu-sched.pdf",        "page": 2,   "element_type": "纯正文",       "note": "调度器 workload 假设列表段落"},
  {"id": "cs-02", "source": "cs/threads-intro.pdf",    "page": 4,   "element_type": "代码块",       "note": "C/pthread #include 多段代码"},
  {"id": "cs-03", "source": "cs/threads-intro.pdf",    "page": 10,  "element_type": "执行追踪表",   "note": "Thread 1/2/PC/eax/counter 多列表格"},
  {"id": "cs-04", "source": "cs/vm-paging.pdf",        "page": 4,   "element_type": "计算/公式",    "note": "VPN/offset 位宽数学推导"},
  {"id": "cs-05", "source": "cs/vm-paging.pdf",        "page": 7,   "element_type": "位域结构图",   "note": "x86 PTE 位位置标注"},
  {"id": "cs-06", "source": "cs/cpu-intro.pdf",        "page": 6,   "element_type": "状态机图",     "note": "Running/Ready/Blocked + Figure caption"},
  {"id": "cl-01", "source": "clinical/Bookshelf_NBK595000.pdf", "page": 33,  "element_type": "纯正文",       "note": "药代动力学四阶段概述"},
  {"id": "cl-02", "source": "clinical/Bookshelf_NBK595000.pdf", "page": 318, "element_type": "多列药物表格", "note": "Table 4.7 五列 Medication Grid，单元格多行"},
  {"id": "cl-03", "source": "clinical/Bookshelf_NBK595000.pdf", "page": 53,  "element_type": "PK曲线图",     "note": "Figure 1.6 半衰期药时曲线 + caption"},
  {"id": "cl-04", "source": "clinical/Bookshelf_NBK595000.pdf", "page": 70,  "element_type": "剂量/稳态文字","note": "半衰期定量描述，含隐式公式"},
  {"id": "cl-05", "source": "clinical/Bookshelf_NBK595000.pdf", "page": 271, "element_type": "结构化药物条目","note": "Vancomycin Route/Dose/Check 嵌套结构"},
  {"id": "lw-01", "source": "law/Criminal-Procedure-July2022_0.pdf", "page": 23, "element_type": "案件引用索引","note": "Case v. Case, U.S. 密集列表"},
  {"id": "lw-02", "source": "law/Criminal-Procedure-July2022_0.pdf", "page": 25, "element_type": "纯正文",       "note": "Chapter 1 Introduction 叙述段"},
  {"id": "lw-03", "source": "law/Criminal-Procedure-July2022_0.pdf", "page": 27, "element_type": "案例分析文本", "note": "Ed Brown v. Mississippi 引用 + 法律推理"},
  {"id": "lw-04", "source": "law/Criminal-Procedure-July2022_0.pdf", "page": 42, "element_type": "修正案/法条",  "note": "第四修正案原文 + Katz 分析"}
]
```

- [ ] **Step 2: Write failing tests**

```python
# tests/parser_selection/__init__.py
# (empty)
```

```python
# tests/parser_selection/test_extract_pages.py
import json
import pytest
import pypdf
from pathlib import Path


def make_test_pdf(path: Path, num_pages: int = 3) -> Path:
    """Create a minimal multi-page PDF for testing."""
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
```

- [ ] **Step 3: Run tests — expect ImportError (module doesn't exist yet)**

```bash
source bookagent.venv/bin/activate
pytest tests/parser_selection/test_extract_pages.py -v
```

Expected: `ImportError: No module named 'eval.parser_selection.scripts.extract_pages'`

- [ ] **Step 4: Create extract_pages.py**

```python
# eval/parser_selection/scripts/extract_pages.py
"""Extract 15 single-page PDFs from source books."""
from __future__ import annotations
import json
from pathlib import Path

import pypdf

_SCRIPTS = Path(__file__).parent
ROOT = _SCRIPTS.parent          # eval/parser_selection/
RAW = ROOT / "fixtures" / "raw"
PAGES = ROOT / "fixtures" / "pages"
CONFIG = _SCRIPTS / "pages.json"


def extract_pages(
    config_path: Path = CONFIG,
    raw_dir: Path = RAW,
    out_dir: Path = PAGES,
) -> list[tuple[str, bool, str]]:
    """Return list of (id, success, message)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads(config_path.read_text())
    results: list[tuple[str, bool, str]] = []

    for entry in config:
        page_id = entry["id"]
        out_path = out_dir / f"{page_id}.pdf"

        if out_path.exists():
            results.append((page_id, True, "skipped"))
            continue

        src = raw_dir / entry["source"]
        if not src.exists():
            results.append((page_id, False, f"source missing: {src}"))
            continue

        reader = pypdf.PdfReader(str(src))
        writer = pypdf.PdfWriter()
        writer.add_page(reader.pages[entry["page"] - 1])  # 1-indexed → 0-indexed
        with open(out_path, "wb") as f:
            writer.write(f)
        results.append((page_id, True, "extracted"))

    return results


if __name__ == "__main__":
    for pid, ok, msg in extract_pages():
        print(f"  {'✓' if ok else '✗'} {pid}: {msg}")
```

Also add `eval/__init__.py` and `eval/parser_selection/__init__.py` and `eval/parser_selection/scripts/__init__.py` so Python treats these as packages:

```bash
touch eval/__init__.py
touch eval/parser_selection/__init__.py
touch eval/parser_selection/scripts/__init__.py
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/parser_selection/test_extract_pages.py -v
```

Expected:
```
tests/parser_selection/test_extract_pages.py::test_extracts_correct_page PASSED
tests/parser_selection/test_extract_pages.py::test_missing_source_returns_error PASSED
tests/parser_selection/test_extract_pages.py::test_idempotent_skips_existing PASSED
3 passed
```

- [ ] **Step 6: Run extract_pages.py against real source PDFs**

```bash
python eval/parser_selection/scripts/extract_pages.py
```

Expected: 15 lines with `✓`, no `✗`. Check:
```bash
ls eval/parser_selection/fixtures/pages/ | wc -l   # → 15
```

- [ ] **Step 7: Commit**

```bash
git add eval/__init__.py eval/parser_selection/__init__.py \
        eval/parser_selection/scripts/__init__.py \
        eval/parser_selection/scripts/pages.json \
        eval/parser_selection/scripts/extract_pages.py \
        tests/parser_selection/__init__.py \
        tests/parser_selection/test_extract_pages.py
git commit -m "feat(w1): add pages.json and extract_pages script with tests"
```

---

### Task 2: requirements-bench.txt + run_bench.py

**Files:**
- Create: `requirements-bench.txt`
- Create: `eval/parser_selection/scripts/run_bench.py`
- Create: `tests/parser_selection/test_run_bench.py`

**Interfaces:**
- Consumes: `fixtures/pages/<id>.pdf` (Task 1 output)
- Consumes: `scripts/pages.json`
- Produces: `results/unstructured/<id>.json` and `results/marker/<id>.json`
- Produces: `results/scorecard.csv` skeleton (30 rows, quality columns empty)
- JSON schema per result file:
  ```json
  {
    "id": "cs-01",
    "parser": "unstructured",
    "elapsed_sec": 1.23,
    "char_count": 842,
    "elements": [{"type": "text", "content": "...", "page_num": 1}],
    "error": null
  }
  ```

- [ ] **Step 1: Create requirements-bench.txt**

```
# Benchmark-only dependencies — not promoted to requirements.txt until parser selected
unstructured[pdf]>=0.16
marker-pdf>=1.6
```

Install:
```bash
source bookagent.venv/bin/activate
pip install -r requirements-bench.txt
```

If there is a dependency conflict between the two libraries, install them and note any warnings — the benchmark still runs as long as both can be imported.

- [ ] **Step 2: Write failing tests (parsers mocked)**

```python
# tests/parser_selection/test_run_bench.py
import json
import csv
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ── helpers ──────────────────────────────────────────────────────────────────

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

    def boom(path):
        raise RuntimeError("parse failed")

    with patch("eval.parser_selection.scripts.run_bench.run_unstructured", side_effect=boom), \
         patch("eval.parser_selection.scripts.run_bench.run_marker",
               return_value=([], 0.1)):
        result = bench_page("cs-01", str(pdf))

    assert result["unstructured"]["error"] is not None
    assert "RuntimeError" in result["unstructured"]["error"]
    assert result["marker"]["error"] is None


# ── write_scorecard_skeleton ──────────────────────────────────────────────────

def test_scorecard_skeleton_structure(tmp_path):
    from eval.parser_selection.scripts.run_bench import write_scorecard_skeleton

    config = [
        {"id": "cs-01", "element_type": "纯正文"},
        {"id": "cs-02", "element_type": "代码块"},
    ]
    write_scorecard_skeleton(config, tmp_path)

    csv_path = tmp_path / "scorecard.csv"
    assert csv_path.exists()
    rows = list(csv.DictReader(open(csv_path)))
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
    assert mtime1 == mtime2  # file not overwritten


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
```

- [ ] **Step 3: Run tests — expect ImportError**

```bash
pytest tests/parser_selection/test_run_bench.py -v
```

Expected: `ImportError: No module named 'eval.parser_selection.scripts.run_bench'`

- [ ] **Step 4: Create run_bench.py**

```python
# eval/parser_selection/scripts/run_bench.py
"""Run Unstructured and Marker on 15 single-page PDFs, collect results."""
from __future__ import annotations
import csv
import json
import time
import traceback
from pathlib import Path

_SCRIPTS = Path(__file__).parent
ROOT = _SCRIPTS.parent
PAGES_DIR = ROOT / "fixtures" / "pages"
RESULTS_DIR = ROOT / "results"
CONFIG = _SCRIPTS / "pages.json"

PARSERS = ["unstructured", "marker"]


# ── parser wrappers ────────────────────────────────────────────────────────────

def run_unstructured(pdf_path: str) -> tuple[list[dict], float]:
    from unstructured.partition.pdf import partition_pdf
    t0 = time.perf_counter()
    elements = partition_pdf(filename=pdf_path, strategy="fast")
    elapsed = time.perf_counter() - t0
    return [
        {"type": e.category.lower(), "content": e.text or "", "page_num": 1}
        for e in elements
    ], elapsed


# Marker models are slow to load — cache them at module level on first call.
_marker_models = None


def run_marker(pdf_path: str) -> tuple[list[dict], float]:
    global _marker_models
    from marker.convert import convert_single_pdf
    from marker.models import load_all_models
    if _marker_models is None:
        _marker_models = load_all_models()
    t0 = time.perf_counter()
    full_text, _images, _meta = convert_single_pdf(pdf_path, _marker_models)
    elapsed = time.perf_counter() - t0
    return [{"type": "markdown", "content": full_text or "", "page_num": 1}], elapsed


_RUNNER = {"unstructured": run_unstructured, "marker": run_marker}


# ── core functions ─────────────────────────────────────────────────────────────

def bench_page(page_id: str, pdf_path: str) -> dict:
    result: dict = {"id": page_id}
    for parser_name in PARSERS:
        fn = _RUNNER[parser_name]
        try:
            elements, elapsed = fn(pdf_path)
            char_count = sum(len(e["content"]) for e in elements)
            result[parser_name] = {
                "elapsed_sec": round(elapsed, 3),
                "char_count": char_count,  # reference only; Markdown inflates Marker value
                "elements": elements,
                "error": None,
            }
        except Exception:
            result[parser_name] = {
                "elapsed_sec": None,
                "char_count": 0,
                "elements": [],
                "error": traceback.format_exc(),
            }
    return result


def write_results(result: dict, out_dir: Path) -> None:
    page_id = result["id"]
    for parser_name in PARSERS:
        parser_dir = out_dir / parser_name
        parser_dir.mkdir(parents=True, exist_ok=True)
        out = parser_dir / f"{page_id}.json"
        out.write_text(
            json.dumps(
                {"id": page_id, "parser": parser_name, **result[parser_name]},
                ensure_ascii=False,
                indent=2,
            )
        )


def write_scorecard_skeleton(config: list[dict], out_dir: Path) -> None:
    csv_path = out_dir / "scorecard.csv"
    if csv_path.exists():
        return
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "parser", "element_type", "detect", "content", "struct", "notes"])
        for entry in config:
            for parser in PARSERS:
                writer.writerow([entry["id"], parser, entry["element_type"], "", "", "", ""])


# ── entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    config = json.loads(CONFIG.read_text())
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for entry in config:
        pid = entry["id"]
        pdf_path = str(PAGES_DIR / f"{pid}.pdf")
        print(f"  Benchmarking {pid} ({entry['element_type']})...")
        result = bench_page(pid, pdf_path)

        for parser in PARSERS:
            err = result[parser].get("error")
            if err:
                print(f"    ✗ {parser}: {err.splitlines()[-1]}")
            else:
                print(f"    ✓ {parser}: {result[parser]['elapsed_sec']}s")

        write_results(result, RESULTS_DIR)

    write_scorecard_skeleton(config, RESULTS_DIR)
    print(f"\nResults → {RESULTS_DIR}")
    print(f"Fill scorecard → {RESULTS_DIR / 'scorecard.csv'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/parser_selection/test_run_bench.py -v
```

Expected:
```
tests/parser_selection/test_run_bench.py::test_bench_page_success PASSED
tests/parser_selection/test_run_bench.py::test_bench_page_parser_error PASSED
tests/parser_selection/test_run_bench.py::test_scorecard_skeleton_structure PASSED
tests/parser_selection/test_run_bench.py::test_scorecard_skeleton_idempotent PASSED
tests/parser_selection/test_run_bench.py::test_write_results_creates_json PASSED
5 passed
```

- [ ] **Step 6: Run benchmark against real pages**

```bash
python eval/parser_selection/scripts/run_bench.py
```

Expected: 15 page entries, each with `✓ unstructured: X.XXXs` and `✓ marker: X.XXXs`. If a parser fails on any page, error is printed but execution continues.

Verify output:
```bash
ls eval/parser_selection/results/unstructured/ | wc -l  # → 15
ls eval/parser_selection/results/marker/ | wc -l         # → 15
wc -l eval/parser_selection/results/scorecard.csv        # → 31 (header + 30 rows)
```

- [ ] **Step 7: Commit**

```bash
git add requirements-bench.txt \
        eval/parser_selection/scripts/run_bench.py \
        tests/parser_selection/test_run_bench.py
git commit -m "feat(w1): add run_bench script with parser wrappers and tests"
```

---

### Task 3: gen_report.py

**Files:**
- Create: `eval/parser_selection/scripts/gen_report.py`
- Create: `tests/parser_selection/test_gen_report.py`

**Interfaces:**
- Consumes: `results/unstructured/<id>.json`, `results/marker/<id>.json`, `results/scorecard.csv`
- Produces: `results/report.md` with speed table, score table, recommendation line
- Consumed by: human decision-maker; also referenced by W5 ablation report template

- [ ] **Step 1: Write failing tests**

```python
# tests/parser_selection/test_gen_report.py
import json
import csv
import pytest
from pathlib import Path


def _make_results(tmp_path: Path, parser: str, pages: list[dict]) -> None:
    d = tmp_path / parser
    d.mkdir(parents=True, exist_ok=True)
    for p in pages:
        out = d / f"{p['id']}.json"
        out.write_text(json.dumps({
            "id": p["id"], "parser": parser,
            "elapsed_sec": p["elapsed_sec"],
            "char_count": p.get("char_count", 100),
            "elements": [], "error": p.get("error"),
        }))


def _make_scorecard(tmp_path: Path, rows: list[dict]) -> None:
    csv_path = tmp_path / "scorecard.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "parser", "element_type",
                                               "detect", "content", "struct", "notes"])
        writer.writeheader()
        writer.writerows(rows)


def _run_report(tmp_path: Path) -> str:
    from eval.parser_selection.scripts.gen_report import main
    main(results_dir=tmp_path, report_path=tmp_path / "report.md")
    return (tmp_path / "report.md").read_text()


def test_report_contains_speed_table(tmp_path):
    pages = [{"id": f"p{i:02d}", "elapsed_sec": 2.0} for i in range(15)]
    _make_results(tmp_path, "unstructured", pages)
    _make_results(tmp_path, "marker", pages)
    _make_scorecard(tmp_path, [
        {"id": f"p{i:02d}", "parser": p, "element_type": "纯正文",
         "detect": "2", "content": "2", "struct": "2", "notes": ""}
        for i in range(15) for p in ("unstructured", "marker")
    ])
    report = _run_report(tmp_path)
    assert "pages/min" in report
    assert "unstructured" in report
    assert "marker" in report


def test_report_recommends_higher_scorer(tmp_path):
    pages_u = [{"id": f"p{i:02d}", "elapsed_sec": 1.0} for i in range(15)]  # fast
    pages_m = [{"id": f"p{i:02d}", "elapsed_sec": 1.5} for i in range(15)]  # also fast
    _make_results(tmp_path, "unstructured", pages_u)
    _make_results(tmp_path, "marker", pages_m)
    # Unstructured gets 2/2/2 per page, Marker gets 1/1/1
    rows = []
    for i in range(15):
        rows.append({"id": f"p{i:02d}", "parser": "unstructured", "element_type": "x",
                     "detect": "2", "content": "2", "struct": "2", "notes": ""})
        rows.append({"id": f"p{i:02d}", "parser": "marker", "element_type": "x",
                     "detect": "1", "content": "1", "struct": "1", "notes": ""})
    _make_scorecard(tmp_path, rows)
    report = _run_report(tmp_path)
    assert "unstructured" in report.split("选定")[1]  # winner mentioned after "选定"


def test_report_disqualifies_slow_parser(tmp_path):
    # unstructured = 10s/page (too slow), marker = 1s/page (fast)
    pages_u = [{"id": f"p{i:02d}", "elapsed_sec": 10.0} for i in range(15)]
    pages_m = [{"id": f"p{i:02d}", "elapsed_sec": 1.0} for i in range(15)]
    _make_results(tmp_path, "unstructured", pages_u)
    _make_results(tmp_path, "marker", pages_m)
    _make_scorecard(tmp_path, [
        {"id": f"p{i:02d}", "parser": p, "element_type": "x",
         "detect": "2", "content": "2", "struct": "2", "notes": ""}
        for i in range(15) for p in ("unstructured", "marker")
    ])
    report = _run_report(tmp_path)
    assert "marker" in report.split("选定")[1]
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/parser_selection/test_gen_report.py -v
```

Expected: `ImportError: No module named 'eval.parser_selection.scripts.gen_report'`

- [ ] **Step 3: Create gen_report.py**

```python
# eval/parser_selection/scripts/gen_report.py
"""Generate parser comparison report from bench results + filled scorecard."""
from __future__ import annotations
import csv
import json
import statistics
from pathlib import Path

_SCRIPTS = Path(__file__).parent
ROOT = _SCRIPTS.parent
_DEFAULT_RESULTS = ROOT / "results"
_DEFAULT_REPORT = ROOT / "results" / "report.md"

PARSERS = ["unstructured", "marker"]
SPEED_TARGET = 15.0  # pages/min


def _load_results(results_dir: Path, parser: str) -> dict[str, dict]:
    return {
        (d := json.loads(f.read_text()))["id"]: d
        for f in sorted((results_dir / parser).glob("*.json"))
    }


def _load_scorecard(results_dir: Path) -> list[dict]:
    with open(results_dir / "scorecard.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _speed_stats(results: dict[str, dict]) -> dict:
    times = [r["elapsed_sec"] for r in results.values()
             if r.get("elapsed_sec") is not None]
    if not times:
        return {"pages_per_min": 0.0, "p50": 0.0, "p95": 0.0}
    times_sorted = sorted(times)
    n = len(times_sorted)
    p50 = statistics.median(times_sorted)
    p95 = times_sorted[min(int(n * 0.95), n - 1)]
    avg = statistics.mean(times)
    return {
        "pages_per_min": round(60.0 / avg, 1) if avg > 0 else 0.0,
        "p50": round(p50, 3),
        "p95": round(p95, 3),
    }


def _score_totals(scorecard: list[dict], parser: str) -> dict[str, int]:
    rows = [r for r in scorecard if r["parser"] == parser]
    totals = {"detect": 0, "content": 0, "struct": 0}
    for row in rows:
        for dim in totals:
            val = row.get(dim, "").strip()
            if val:
                totals[dim] += int(val)
    totals["total"] = sum(totals.values())
    return totals


def main(
    results_dir: Path = _DEFAULT_RESULTS,
    report_path: Path = _DEFAULT_REPORT,
) -> None:
    all_results = {p: _load_results(results_dir, p) for p in PARSERS}
    scorecard = _load_scorecard(results_dir)

    speed = {p: _speed_stats(all_results[p]) for p in PARSERS}
    scores = {p: _score_totals(scorecard, p) for p in PARSERS}

    lines: list[str] = ["# 解析器选型对比报告\n"]

    # Speed table
    lines += [
        "## 1. 速度对比\n",
        "| 解析器 | pages/min | p50 延迟(s) | p95 延迟(s) | 达标(≥15) |",
        "|---|---|---|---|---|",
    ]
    for p in PARSERS:
        s = speed[p]
        ok = "✅" if s["pages_per_min"] >= SPEED_TARGET else "❌"
        lines.append(f"| {p} | {s['pages_per_min']} | {s['p50']} | {s['p95']} | {ok} |")

    # Score table
    lines += [
        "\n## 2. 人工评分汇总（满分 90）\n",
        "| 解析器 | detect(/30) | content(/30) | struct(/30) | 总分(/90) |",
        "|---|---|---|---|---|",
    ]
    for p in PARSERS:
        sc = scores[p]
        lines.append(
            f"| {p} | {sc['detect']} | {sc['content']} | {sc['struct']} | {sc['total']} |"
        )

    # Recommendation
    lines.append("\n## 3. 选定建议\n")
    qualified = [p for p in PARSERS if speed[p]["pages_per_min"] >= SPEED_TARGET]

    if not qualified:
        lines.append("❌ **两个解析器均未达速度要求（≥15 pages/min），需调整策略后重测。**")
        winner = None
    elif len(qualified) == 1:
        winner = qualified[0]
        loser = [p for p in PARSERS if p != winner][0]
        lines.append(
            f"✅ **选定：`{winner}`**（`{loser}` 速度不达标，直接出局）"
        )
    else:
        winner = max(qualified, key=lambda p: scores[p]["total"])
        other = [p for p in qualified if p != winner][0]
        lines.append(
            f"✅ **选定：`{winner}`**（速度均达标；人工总分 {scores[winner]['total']} > {scores[other]['total']}）"
        )

    if winner:
        lines.append(
            f"\n**下一步：** 在 `requirements.txt` 中取消 `{winner}` 注释，"
            f"删除 `requirements-bench.txt`，合并 `feat/w1-parser-selection` → `main`。"
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report → {report_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/parser_selection/test_gen_report.py -v
```

Expected:
```
tests/parser_selection/test_gen_report.py::test_report_contains_speed_table PASSED
tests/parser_selection/test_gen_report.py::test_report_recommends_higher_scorer PASSED
tests/parser_selection/test_gen_report.py::test_report_disqualifies_slow_parser PASSED
3 passed
```

- [ ] **Step 5: Commit**

```bash
git add eval/parser_selection/scripts/gen_report.py \
        tests/parser_selection/test_gen_report.py
git commit -m "feat(w1): add gen_report script with recommendation logic and tests"
```

---

### Task 4: pipeline/parse/ interface skeleton

**Files:**
- Create: `pipeline/parse/__init__.py`
- Create: `pipeline/parse/base.py`
- Create: `pipeline/parse/unstructured.py`
- Create: `pipeline/parse/marker.py`
- Create: `tests/parser_selection/test_parse_interface.py`

**Interfaces:**
- Produces: `Element(type, content, page_num, metadata)` dataclass
- Produces: `Parser` ABC with `parse(pdf_path: str) -> list[Element]`
- Produces: `UnstructuredParser`, `MarkerParser` — both raise `NotImplementedError` (stubs)
- Consumed by: W2 `chunk` layer once parser is selected and adapters are filled in

- [ ] **Step 1: Write failing tests**

```python
# tests/parser_selection/test_parse_interface.py
import pytest
from pipeline.parse import Element, Parser
from pipeline.parse.unstructured import UnstructuredParser
from pipeline.parse.marker import MarkerParser


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

    p = EchoParser()
    result = p.parse("test.pdf")
    assert len(result) == 1
    assert result[0].content == "test.pdf"
    assert result[0].type == "text"


def test_unstructured_parser_stub_raises():
    p = UnstructuredParser()
    with pytest.raises(NotImplementedError):
        p.parse("any.pdf")


def test_marker_parser_stub_raises():
    p = MarkerParser()
    with pytest.raises(NotImplementedError):
        p.parse("any.pdf")
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/parser_selection/test_parse_interface.py -v
```

Expected: `ImportError: No module named 'pipeline.parse'`

- [ ] **Step 3: Create pipeline/parse/ files**

```python
# pipeline/parse/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Element:
    type: str       # "text" | "table" | "formula" | "figure" | "code"
    content: str    # Markdown / LaTeX / plain text
    page_num: int   # 1-indexed
    metadata: dict = field(default_factory=dict)


class Parser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> list[Element]: ...
```

```python
# pipeline/parse/unstructured.py
from .base import Element, Parser


class UnstructuredParser(Parser):
    """Unstructured adapter — implement after parser selection benchmark."""

    def parse(self, pdf_path: str) -> list[Element]:
        raise NotImplementedError(
            "UnstructuredParser not yet implemented; "
            "run the parser selection benchmark first."
        )
```

```python
# pipeline/parse/marker.py
from .base import Element, Parser


class MarkerParser(Parser):
    """Marker-pdf adapter — implement after parser selection benchmark."""

    def parse(self, pdf_path: str) -> list[Element]:
        raise NotImplementedError(
            "MarkerParser not yet implemented; "
            "run the parser selection benchmark first."
        )
```

```python
# pipeline/parse/__init__.py
from .base import Element, Parser
from .unstructured import UnstructuredParser
from .marker import MarkerParser

__all__ = ["Element", "Parser", "UnstructuredParser", "MarkerParser"]
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/parser_selection/test_parse_interface.py -v
```

Expected:
```
tests/parser_selection/test_parse_interface.py::test_element_default_metadata PASSED
tests/parser_selection/test_parse_interface.py::test_element_with_metadata PASSED
tests/parser_selection/test_parse_interface.py::test_parser_abstract_cannot_instantiate PASSED
tests/parser_selection/test_parse_interface.py::test_parser_concrete_subclass_works PASSED
tests/parser_selection/test_parse_interface.py::test_unstructured_parser_stub_raises PASSED
tests/parser_selection/test_parse_interface.py::test_marker_parser_stub_raises PASSED
6 passed
```

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass, including pre-existing `tests/agent/` tests.

- [ ] **Step 6: Commit**

```bash
git add pipeline/parse/__init__.py pipeline/parse/base.py \
        pipeline/parse/unstructured.py pipeline/parse/marker.py \
        tests/parser_selection/test_parse_interface.py
git commit -m "feat(w1): add pipeline/parse abstract interface and stub adapters"
```

---

## Post-Benchmark Steps (Manual, Not Coded)

After running `run_bench.py` and filling `scorecard.csv`:

```bash
# Generate report
python eval/parser_selection/scripts/gen_report.py
cat eval/parser_selection/results/report.md
```

Then follow the report's recommendation:

1. In `requirements.txt`, uncomment the winning parser line
2. Delete `requirements-bench.txt`
3. Fill in the winning parser's adapter in `pipeline/parse/`
4. Open PR: `feat/w1-parser-selection → main`

---

## Self-Review

**Spec coverage:**
- §2 Directory structure → reflected in File Map and every task ✓
- §3 pages.json (15 entries) → Task 1 Step 1 ✓
- §4.1 extract_pages.py → Task 1 ✓
- §4.2 run_bench.py + scorecard skeleton → Task 2 ✓
- §4.3 gen_report.py → Task 3 ✓
- §5 Human scoring (detect/content/struct 0–2) → scorecard columns in Task 2, scoring in Task 3 ✓
- §6 Element + Parser ABC → Task 4 ✓
- §7 Decision rule (speed first, then score, then license) → gen_report.py recommendation logic ✓
- §9 Milestones → each task maps to a milestone ✓

**Placeholder scan:** No TBD / TODO / "implement later" present.

**Type consistency:** `Element` fields (`type`, `content`, `page_num`, `metadata`) consistent across base.py, stubs, and tests. `bench_page` returns dict with keys matching `write_results` expectations. `gen_report.main()` signature `(results_dir, report_path)` consistent with test helpers.
