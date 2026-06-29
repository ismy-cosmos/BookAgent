"""Ingest books into Chroma vector store.

Usage:
    python scripts/ingest.py --book-id ostep-cs --dir eval/testset/cs/raw/book/
    python scripts/ingest.py --book-id ostep-cs --file chapter01.pdf --file audio.mp3
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# Ensure repo root is on path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.chunk import Chunker
from pipeline.embed import Embedder
from pipeline.parse.audio import AudioParser
from pipeline.parse.epub import EPUBParser
from pipeline.parse.image import VLMImageParser
from pipeline.parse.marker import MarkerParser
from pipeline.store import ChromaStore

_AUDIO_EXTS = {".mp3", ".wav", ".flac"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".svg"}
_ALL_EXTS = {".pdf", ".epub"} | _AUDIO_EXTS | _IMAGE_EXTS
_CHROMA_DIR = os.environ.get("CHROMA_DIR", ".chroma")
_DEFAULT_BATCH = 64


def _sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def _manifest_path(manifest_dir: str, book_id: str) -> Path:
    return Path(manifest_dir) / f"{book_id}.json"


def _load_manifest(manifest_dir: str, book_id: str) -> dict:
    p = _manifest_path(manifest_dir, book_id)
    if not p.exists():
        return {"sha256_to_file": {}}
    return json.loads(p.read_text())


def _save_manifest(manifest_dir: str, book_id: str, data: dict) -> None:
    p = _manifest_path(manifest_dir, book_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def _resolve_source_file(filename: str, manifest: dict) -> str:
    existing = set(manifest["sha256_to_file"].values())
    if filename not in existing:
        return filename
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    i = 1
    while True:
        candidate = f"{stem}({i}){suffix}"
        if candidate not in existing:
            return candidate
        i += 1


def _collect_files(files: list[str], directory: str | None) -> list[str]:
    result = list(files)
    if directory:
        for p in sorted(Path(directory).iterdir()):
            if p.is_file() and p.suffix.lower() in _ALL_EXTS:
                result.append(str(p))
    return result


def _route_parser(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return MarkerParser()
    if ext == ".epub":
        return EPUBParser()
    if ext in _AUDIO_EXTS:
        return AudioParser()
    if ext in _IMAGE_EXTS:
        return VLMImageParser()
    raise ValueError(f"Unsupported file type: {ext}")


def _ingest_file(
    file_path: str,
    book_id: str,
    source_file: str,
    chunker: Chunker,
    embedder: Embedder,
    store: ChromaStore,
    batch_size: int,
) -> int:
    ext = Path(file_path).suffix.lower()

    if ext in _AUDIO_EXTS:
        parser = AudioParser()
        chunks = parser.parse_to_chunks(file_path, book_id)
    else:
        parser = _route_parser(file_path)
        elements = parser.parse(file_path)
        chunks = chunker.chunk(elements, book_id=book_id, source_file=source_file)

    if not chunks:
        print(f"  [warn] No chunks produced from {file_path}")
        return 0

    # Override source_file in chunks to the resolved name
    for c in chunks:
        c.source_file = source_file

    # Embed and store in batches
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.content for c in batch]
        embeddings = embedder.embed(texts)
        store.add_chunks(book_id, batch, embeddings)
        total += len(batch)
        print(f"  Stored {total}/{len(chunks)} chunks...", end="\r")

    print(f"  Stored {total} chunks from {source_file}          ")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest files into Chroma vector store")
    parser.add_argument("--book-id", required=True, help="Chroma collection name")
    parser.add_argument("--file", action="append", default=[], dest="files",
                        help="File to ingest (repeatable)")
    parser.add_argument("--dir", help="Directory: ingest all supported files")
    parser.add_argument("--chroma-dir", default=_CHROMA_DIR)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH)
    args = parser.parse_args()

    if not args.files and not args.dir:
        parser.error("Provide at least --file or --dir")

    all_files = _collect_files(args.files, args.dir)
    if not all_files:
        print("No files found.")
        return

    manifest_dir = str(Path(args.chroma_dir) / ".manifests")
    chunker = Chunker()
    embedder = Embedder()
    store = ChromaStore(persist_dir=args.chroma_dir)

    total_chunks = 0
    for file_path in all_files:
        manifest = _load_manifest(manifest_dir, args.book_id)
        sha = _sha256(file_path)

        if sha in manifest["sha256_to_file"]:
            print(f"Skip (already ingested): {file_path}")
            continue

        filename = Path(file_path).name
        source_file = _resolve_source_file(filename, manifest)
        print(f"Ingesting: {file_path} → {source_file}")

        n = _ingest_file(
            file_path, args.book_id, source_file,
            chunker, embedder, store, args.batch_size,
        )
        manifest["sha256_to_file"][sha] = source_file
        _save_manifest(manifest_dir, args.book_id, manifest)
        total_chunks += n

    print(f"\nDone. Total chunks ingested: {total_chunks}")
    print(f"Chroma collection '{args.book_id}' now has {store.count(args.book_id)} chunks.")


if __name__ == "__main__":
    main()
