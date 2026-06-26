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


_marker_models = None  # loaded once on first call


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


import sys as _sys


# ── core functions ─────────────────────────────────────────────────────────────

def bench_page(page_id: str, pdf_path: str) -> dict:
    result: dict = {"id": page_id}
    _mod = _sys.modules[__name__]
    for parser_name in PARSERS:
        fn = getattr(_mod, f"run_{parser_name}")
        try:
            elements, elapsed = fn(pdf_path)
            char_count = sum(len(e["content"]) for e in elements)
            result[parser_name] = {
                "elapsed_sec": round(elapsed, 3),
                "char_count": char_count,
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
                print(f"    ✓ {parser}: {result[parser]['elapsed_sec']}s  {result[parser]['char_count']}ch")

        write_results(result, RESULTS_DIR)

    write_scorecard_skeleton(config, RESULTS_DIR)
    print(f"\nResults → {RESULTS_DIR}")
    print(f"Fill scorecard → {RESULTS_DIR / 'scorecard.csv'}")


if __name__ == "__main__":
    main()
