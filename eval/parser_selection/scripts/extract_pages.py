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
