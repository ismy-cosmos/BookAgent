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
import time
import traceback
from datetime import datetime
from pathlib import Path

# Ensure repo root is on path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass, field

from pipeline.chunk import Chunker
from pipeline.embed import Embedder
from pipeline.parse import parse_cache
from pipeline.parse.audio import AudioParser
from pipeline.parse.epub import EPUBParser
from pipeline.parse.figure_batch import resolve_figures
from pipeline.parse.image import VLMImageParser, _resize_to_limit, load_image_element
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
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)


def _failures_path(manifest_dir: str, book_id: str) -> Path:
    return Path(manifest_dir) / f"{book_id}.failures.json"


def _save_failures(
    manifest_dir: str,
    book_id: str,
    failures: list[dict],
    not_attempted: list[str],
    aborted_early: bool,
) -> None:
    p = _failures_path(manifest_dir, book_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "run_at": datetime.now().isoformat(),
        "aborted_early": aborted_early,
        "failures": failures,
        "not_attempted": not_attempted,
    }, indent=2))


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


def _remove_by_source_file(manifest: dict, source_file: str) -> tuple[dict, bool]:
    """从 manifest 里摘掉指向 source_file 的那条 sha256 记录，不就地修改传入的 manifest。"""
    sha_to_remove = None
    for sha, fname in manifest["sha256_to_file"].items():
        if fname == source_file:
            sha_to_remove = sha
            break
    if sha_to_remove is None:
        return manifest, False
    updated = {"sha256_to_file": dict(manifest["sha256_to_file"])}
    del updated["sha256_to_file"][sha_to_remove]
    return updated, True


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


@dataclass
class _PendingFile:
    """阶段1解析完、等待阶段2/3处理的文件。elements 与 chunks 二选一：
    音频在解析时直接产出 chunks；其余格式产出 elements 待分块。"""
    file_path: str
    source_file: str
    sha: str
    elements: list | None = None
    chunks: list | None = None
    image_shas: list = field(default_factory=list)


def _parse_file(file_path: str, book_id: str, source_file: str):
    """阶段1：解析单个文件。返回 (elements, chunks)。"""
    ext = Path(file_path).suffix.lower()
    if ext in _AUDIO_EXTS:
        chunks = AudioParser().parse_to_chunks(file_path, book_id, source_file=source_file)
        return None, chunks
    if ext in _IMAGE_EXTS:
        # 独立图片：只读字节不调 VLM，描述在阶段2批量生成
        return [load_image_element(file_path)], None
    parser = _route_parser(file_path)
    return parser.parse(file_path), None


def _resize_figure_elements(elements: list | None) -> None:
    """阶段1 解析完/从缓存加载后统一做一次缩放，阶段2 不再重复缩放。"""
    if not elements:
        return
    for elem in elements:
        if elem.type == "figure" and elem.metadata.get("image_bytes"):
            elem.metadata["image_bytes"] = _resize_to_limit(elem.metadata["image_bytes"])


def _figure_image_shas(elements: list | None) -> list[str]:
    if not elements:
        return []
    return [
        hashlib.sha256(elem.metadata["image_bytes"]).hexdigest()
        for elem in elements
        if elem.type == "figure" and elem.metadata.get("image_bytes")
    ]


def _store_file(
    pending: _PendingFile,
    book_id: str,
    chunker: Chunker,
    embedder: Embedder,
    store: ChromaStore,
    batch_size: int,
) -> int:
    """阶段3：分块（音频跳过）→ 嵌入 → 入库。"""
    if pending.chunks is not None:
        chunks = pending.chunks
    else:
        chunks = chunker.chunk(pending.elements, book_id=book_id,
                               source_file=pending.source_file)

    if not chunks:
        print(f"  [warn] No chunks produced from {pending.file_path}")
        return 0

    for c in chunks:
        c.source_file = pending.source_file

    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        existing = store.get(book_id, [c.chunk_id for c in batch])
        existing_ids = {r["chunk_id"] for r in existing}
        missing = [c for c in batch if c.chunk_id not in existing_ids]
        if missing:
            texts = [c.content for c in missing]
            embeddings = embedder.embed(texts)
            store.add_chunks(book_id, missing, embeddings)
        total += len(batch)
        print(f"  Stored {total}/{len(chunks)} chunks...", end="\r")

    print(f"  Stored {total} chunks from {pending.source_file}          ")
    return total


@dataclass
class IngestResult:
    total_chunks: int
    failures: list[dict]
    not_attempted: list[str]
    aborted_early: bool


def run_ingest(
    book_id: str,
    file_paths: list[str],
    chroma_dir: str = _CHROMA_DIR,
    batch_size: int = _DEFAULT_BATCH,
) -> IngestResult:
    manifest_dir = str(Path(chroma_dir) / ".manifests")
    chunker = Chunker()
    embedder = Embedder()
    store = ChromaStore(persist_dir=chroma_dir)

    max_consecutive_failures = int(os.environ.get("INGEST_MAX_CONSECUTIVE_FAILURES", "0"))

    total_chunks = 0
    failures: list[dict] = []
    not_attempted: list[str] = []
    consecutive_failures = 0
    aborted_early = False

    def _record_failure(file_path: str, e: Exception) -> None:
        print(f"[error] Failed to ingest {file_path}: {type(e).__name__}: {e}")
        traceback.print_exc()
        failures.append({
            "file": file_path,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat(),
        })

    # ── 阶段1：全部解析（sha 跳过检查在解析前——解析是最贵的一步）──
    t_stage1 = time.perf_counter()
    pending: list[_PendingFile] = []
    manifest = _load_manifest(manifest_dir, book_id)
    manifest_view = {"sha256_to_file": dict(manifest["sha256_to_file"])}
    for idx, file_path in enumerate(file_paths):
        try:
            sha = _sha256(file_path)
            if sha in manifest["sha256_to_file"]:
                print(f"Skip (already ingested): {file_path}")
                consecutive_failures = 0
                continue
            filename = Path(file_path).name
            source_file = _resolve_source_file(filename, manifest_view)
            manifest_view["sha256_to_file"][f"pending:{sha}"] = source_file
            print(f"Parsing: {file_path} → {source_file}")
            cached = parse_cache.get(chroma_dir, book_id, sha)
            if cached is not None:
                elements, chunks = cached
                _resize_figure_elements(elements)  # 幂等安全网：缓存里本就是缩放后的字节，这里兜住旧版本缓存
                print("  (解析缓存命中，跳过重新解析)")
            else:
                elements, chunks = _parse_file(file_path, book_id, source_file)
                _resize_figure_elements(elements)
                parse_cache.set(chroma_dir, book_id, sha, elements, chunks)
            image_shas = _figure_image_shas(elements)
            pending.append(_PendingFile(
                file_path=file_path, source_file=source_file, sha=sha,
                elements=elements, chunks=chunks, image_shas=image_shas,
            ))
            consecutive_failures = 0
        except Exception as e:
            _record_failure(file_path, e)
            consecutive_failures += 1
            if max_consecutive_failures and consecutive_failures >= max_consecutive_failures:
                print(f"\n[abort] {consecutive_failures} 个文件连续解析失败，疑似系统性问题，已中止批次。")
                not_attempted = file_paths[idx + 1:]
                aborted_early = True
                break

    print(f"\n阶段1 解析完成，{len(pending)} 个文件，耗时 {time.perf_counter() - t_stage1:.1f}s")

    # ── 阶段2：VLM 批量描述（先释放 marker 模型腾显存）──
    t_stage2 = time.perf_counter()
    files_with_elements = [p.elements for p in pending if p.elements is not None]
    if files_with_elements:
        MarkerParser.release_models()
        stats = resolve_figures(files_with_elements, chroma_dir=chroma_dir, book_id=book_id)
        if stats.described or stats.degraded or stats.no_bytes:
            print(f"\nVLM 批量描述：成功 {stats.described} / 降级 {stats.degraded}"
                  f" / 无字节跳过 {stats.no_bytes}"
                  + ("（熔断已触发）" if stats.breaker_tripped else ""))
    print(f"阶段2 VLM 批量描述完成，耗时 {time.perf_counter() - t_stage2:.1f}s")

    # ── 阶段3：逐文件分块 → 嵌入 → 入库 ──
    t_stage3 = time.perf_counter()
    for p in pending:
        try:
            ext = Path(p.file_path).suffix.lower()
            if ext in _IMAGE_EXTS:
                elem = p.elements[0]
                if elem.metadata.get("vlm_status") != "described":
                    raise RuntimeError(
                        "VLM 描述失败——独立图片文件没有占位符可回退，整个文件视为失败")
            n = _store_file(p, book_id, chunker, embedder, store, batch_size)
            manifest = _load_manifest(manifest_dir, book_id)
            manifest["sha256_to_file"][p.sha] = p.source_file
            _save_manifest(manifest_dir, book_id, manifest)
            total_chunks += n
            consecutive_failures = 0
        except Exception as e:
            _record_failure(p.file_path, e)
            try:
                store.delete_by_source(book_id, p.source_file)
            except Exception as cleanup_exc:
                print(f"[warn] Rollback for {p.file_path} also failed: {cleanup_exc}")
            consecutive_failures += 1
            if max_consecutive_failures and consecutive_failures >= max_consecutive_failures:
                print(f"\n[abort] {consecutive_failures} 个文件连续失败，疑似系统性问题，已中止批次。")
                idx3 = pending.index(p)
                not_attempted = [q.file_path for q in pending[idx3 + 1:]]
                aborted_early = True
                break

    _save_failures(manifest_dir, book_id, failures, not_attempted, aborted_early)

    print(f"阶段3 入库完成，耗时 {time.perf_counter() - t_stage3:.1f}s")
    print(f"\nDone. Total chunks ingested: {total_chunks}")
    print(f"Chroma collection '{book_id}' now has {store.count(book_id)} chunks.")

    if failures:
        print(f"\n{len(failures)} file(s) failed:")
        for f in failures:
            print(f"  - {f['file']}: {f['error_type']}: {f['error_message']}")
    if not_attempted:
        print(f"\n{len(not_attempted)} file(s) not attempted (batch aborted early):")
        for fp in not_attempted:
            print(f"  - {fp}")

    return IngestResult(
        total_chunks=total_chunks,
        failures=failures,
        not_attempted=not_attempted,
        aborted_early=aborted_early,
    )


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

    result = run_ingest(args.book_id, all_files, chroma_dir=args.chroma_dir,
                        batch_size=args.batch_size)

    if result.failures or result.aborted_early:
        sys.exit(1)


if __name__ == "__main__":
    main()
