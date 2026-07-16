"""Dump all chunks for a book_id from BookAgent's own Chroma store to JSON.

Used for deriving Hit@5 ground truth (support_chunks) by matching CS testset
source_location entries against real chunk content/page/time metadata.

Usage:
    python scripts/dump_chunks_for_eval.py cs-eval-60 .chroma-eval-cs60 eval/chunks_dump_bookagent.json
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.store import ChromaStore


def main(book_id: str, chroma_dir: str, out_path: str) -> None:
    store = ChromaStore(persist_dir=chroma_dir)
    collection = store._collection(book_id)
    data = collection.get()
    rows = []
    for chunk_id, content, metadata in zip(data["ids"], data["documents"], data["metadatas"]):
        rows.append({
            "chunk_id": chunk_id,
            "source_file": metadata.get("source_file"),
            "element_type": metadata.get("element_type"),
            "page_start": metadata.get("page_start") or None,
            "page_end": metadata.get("page_end") or None,
            "start_sec": metadata.get("start_sec") or None,
            "end_sec": metadata.get("end_sec") or None,
            "content": content,
        })
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"Dumped {len(rows)} chunks -> {out_path}")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "cs-eval-60"
    chroma_dir = sys.argv[2] if len(sys.argv) > 2 else ".chroma-eval-cs60"
    out = sys.argv[3] if len(sys.argv) > 3 else "eval/chunks_dump_bookagent.json"
    main(book_id, chroma_dir, out)
