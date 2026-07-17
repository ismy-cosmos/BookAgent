"""Dump parse→chunk output to JSONL for inspection and offline analysis.

Usage:
    python scripts/dump_chunks.py                          # all 8 OSTEP CS books
    python scripts/dump_chunks.py --file cpu-intro.pdf    # single file

Output: eval/testset/cs/chunks/<stem>.jsonl  (one line = one chunk, all fields)
"""
from __future__ import annotations
import argparse
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 理由见 pipeline/offline_mode.py。这是独立脚本入口（不经过 run_api.py/
# ingest.py），MarkerParser 在这里直接实例化，之前完全没有离线保护——真撞上
# HuggingFace 服务故障会原样卡死。
from pipeline.offline_mode import force_offline
force_offline()

from pipeline.chunk import Chunker
from pipeline.parse.marker import MarkerParser

_BOOK_DIR = Path("eval/testset/cs/raw/book")
_OUT_DIR = Path("eval/testset/cs/chunks")
_BOOK_ID = "ostep-cs"


def _dump(pdf_path: Path, chunker: Chunker, parser: MarkerParser) -> list[dict]:
    print(f"parsing  {pdf_path.name} ...", end=" ", flush=True)
    elements = parser.parse(str(pdf_path))
    chunks = chunker.chunk(elements, book_id=_BOOK_ID, source_file=pdf_path.name)
    print(f"{len(elements)} elements → {len(chunks)} chunks")

    records = [dataclasses.asdict(c) for c in chunks]

    out_path = _OUT_DIR / f"{pdf_path.stem}.jsonl"
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return records


def _summarise(all_records: list[dict]) -> None:
    if not all_records:
        return
    tok = [r["token_count"] for r in all_records]
    types: dict[str, int] = {}
    for r in all_records:
        types[r["element_type"]] = types.get(r["element_type"], 0) + 1

    print(f"\n{'='*55}")
    print(f"  total chunks : {len(all_records)}")
    print(f"  tokens       : min={min(tok)}  avg={sum(tok)//len(tok)}  max={max(tok)}")
    print(f"  element types: {types}")
    print(f"  output dir   : {_OUT_DIR.resolve()}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="Single PDF filename (basename only)")
    args = ap.parse_args()

    if args.file:
        pdfs = [_BOOK_DIR / args.file]
    else:
        pdfs = sorted(_BOOK_DIR.glob("*.pdf"))

    if not pdfs:
        print("No PDFs found.")
        return

    parser = MarkerParser()
    chunker = Chunker()
    all_records: list[dict] = []

    for pdf in pdfs:
        all_records.extend(_dump(pdf, chunker, parser))

    _summarise(all_records)


if __name__ == "__main__":
    main()