import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from pipeline.chunk.schema import Chunk
from pipeline.parse.base import Element
from scripts.ingest import (
    _sha256,
    _load_manifest,
    _save_manifest,
    _resolve_source_file,
    _remove_by_source_file,
    _collect_files,
    _route_parser,
    _parse_file,
    _store_file,
    _PendingFile,
    run_ingest,
    IngestResult,
    main,
)


def test_sha256_stable(tmp_path):
    f = tmp_path / "x.pdf"
    f.write_bytes(b"hello")
    h1 = _sha256(str(f))
    h2 = _sha256(str(f))
    assert h1 == h2
    assert len(h1) == 64


def test_sha256_different_content(tmp_path):
    f1 = tmp_path / "a.pdf"; f1.write_bytes(b"aaa")
    f2 = tmp_path / "b.pdf"; f2.write_bytes(b"bbb")
    assert _sha256(str(f1)) != _sha256(str(f2))


def test_load_manifest_missing_file(tmp_path):
    m = _load_manifest(str(tmp_path / ".manifests"), "b")
    assert m == {"sha256_to_file": {}}


def test_save_and_load_manifest(tmp_path):
    manifest_dir = str(tmp_path / ".manifests")
    data = {"sha256_to_file": {"abc": "ch01.pdf"}}
    _save_manifest(manifest_dir, "b", data)
    loaded = _load_manifest(manifest_dir, "b")
    assert loaded == data


def test_save_manifest_uses_atomic_replace(tmp_path, monkeypatch):
    from pathlib import Path as _Path
    manifest_dir = str(tmp_path / ".manifests")
    calls = []
    original_replace = _Path.replace

    def spy_replace(self, target):
        calls.append((str(self), str(target)))
        return original_replace(self, target)

    monkeypatch.setattr(_Path, "replace", spy_replace)
    _save_manifest(manifest_dir, "b", {"sha256_to_file": {"abc": "x.pdf"}})

    assert len(calls) == 1
    assert calls[0][0].endswith(".tmp")
    assert calls[0][1].endswith("b.json")


def test_save_manifest_no_tmp_file_left_after_success(tmp_path):
    manifest_dir = str(tmp_path / ".manifests")
    _save_manifest(manifest_dir, "b", {"sha256_to_file": {}})
    assert not (Path(manifest_dir) / "b.json.tmp").exists()


def test_resolve_source_file_no_conflict():
    manifest = {"sha256_to_file": {}}
    result = _resolve_source_file("chapter01.pdf", manifest)
    assert result == "chapter01.pdf"


def test_resolve_source_file_name_conflict():
    manifest = {"sha256_to_file": {"oldhash": "chapter01.pdf"}}
    result = _resolve_source_file("chapter01.pdf", manifest)
    assert result == "chapter01(1).pdf"


def test_resolve_source_file_multiple_conflicts():
    manifest = {
        "sha256_to_file": {
            "h1": "chapter01.pdf",
            "h2": "chapter01(1).pdf",
        }
    }
    result = _resolve_source_file("chapter01.pdf", manifest)
    assert result == "chapter01(2).pdf"


def test_remove_by_source_file_found():
    manifest = {"sha256_to_file": {"abc": "ch01.pdf", "def": "ch02.pdf"}}
    updated, removed = _remove_by_source_file(manifest, "ch01.pdf")
    assert removed is True
    assert updated == {"sha256_to_file": {"def": "ch02.pdf"}}
    # 原 dict 不能被就地改掉，调用方可能还持有旧引用
    assert manifest["sha256_to_file"] == {"abc": "ch01.pdf", "def": "ch02.pdf"}


def test_remove_by_source_file_not_found():
    manifest = {"sha256_to_file": {"abc": "ch01.pdf"}}
    updated, removed = _remove_by_source_file(manifest, "missing.pdf")
    assert removed is False
    assert updated == manifest


def test_collect_files_from_dir(tmp_path):
    (tmp_path / "ch01.pdf").write_bytes(b"x")
    (tmp_path / "ch02.epub").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_bytes(b"x")
    files = _collect_files([], str(tmp_path))
    exts = {Path(f).suffix for f in files}
    assert ".pdf" in exts
    assert ".epub" in exts
    assert ".txt" not in exts


def test_route_parser_pdf():
    p = _route_parser("chapter.pdf")
    from pipeline.parse.marker import MarkerParser
    assert isinstance(p, MarkerParser)


def test_route_parser_epub():
    p = _route_parser("book.epub")
    from pipeline.parse.epub import EPUBParser
    assert isinstance(p, EPUBParser)


def test_route_parser_audio():
    p = _route_parser("lecture.mp3")
    from pipeline.parse.audio import AudioParser
    assert isinstance(p, AudioParser)


def test_route_parser_image():
    p = _route_parser("figure.png")
    from pipeline.parse.image import VLMImageParser
    assert isinstance(p, VLMImageParser)


def test_route_parser_unknown_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        _route_parser("data.csv")


# ── _parse_file / _store_file / _PendingFile ─────────────────────────────────

def _pending(file_path="ch01.pdf", source_file="ch01.pdf", elements=None, chunks=None):
    return _PendingFile(file_path=file_path, source_file=source_file,
                        sha="deadbeef", elements=elements, chunks=chunks)


def test_parse_file_audio_returns_chunks(tmp_path):
    from scripts.ingest import _always_false

    f = tmp_path / "lecture.mp3"
    f.write_bytes(b"fake audio")
    chunk = Chunk(chunk_id="b/lecture.mp3/0000", book_id="b", source_file="lecture.mp3",
                  element_type="audio", content="hello", token_count=1)
    mock_parser = MagicMock()
    mock_parser.parse_to_chunks.return_value = [chunk]

    with patch("scripts.ingest.AudioParser", return_value=mock_parser):
        elements, chunks = _parse_file(str(f), "b", "lecture.mp3")

    assert elements is None
    assert chunks == [chunk]
    mock_parser.parse_to_chunks.assert_called_once_with(
        str(f), "b", source_file="lecture.mp3", should_pause=_always_false)


def test_parse_file_audio_passes_through_custom_should_pause(tmp_path):
    f = tmp_path / "lecture.mp3"
    f.write_bytes(b"fake audio")
    mock_parser = MagicMock()
    mock_parser.parse_to_chunks.return_value = []
    custom_pause = lambda: True

    with patch("scripts.ingest.AudioParser", return_value=mock_parser):
        _parse_file(str(f), "b", "lecture.mp3", should_pause=custom_pause)

    mock_parser.parse_to_chunks.assert_called_once_with(
        str(f), "b", source_file="lecture.mp3", should_pause=custom_pause)


def test_parse_file_image_uses_load_image_element_no_vlm(tmp_path):
    f = tmp_path / "fig.png"
    f.write_bytes(b"\x89PNG fake")
    fake_elem = MagicMock()

    with patch("scripts.ingest.load_image_element", return_value=fake_elem) as mock_load:
        elements, chunks = _parse_file(str(f), "b", "fig.png")

    mock_load.assert_called_once_with(str(f))
    assert elements == [fake_elem]
    assert chunks is None


def test_parse_file_pdf_routes_to_parser(tmp_path):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"fake pdf")
    mock_parser = MagicMock()
    mock_parser.parse.return_value = ["element1"]

    with patch("scripts.ingest._route_parser", return_value=mock_parser):
        elements, chunks = _parse_file(str(f), "b", "ch01.pdf")

    assert elements == ["element1"]
    assert chunks is None


def test_store_file_chunks_elements_and_batches(tmp_path):
    chunks = [
        Chunk(chunk_id=f"b/ch01.pdf/p0001/{i:04d}", book_id="b", source_file="ch01.pdf",
              element_type="text", content=f"chunk {i}", token_count=1)
        for i in range(5)
    ]
    chunker = MagicMock(); chunker.chunk.return_value = chunks
    embedder = MagicMock()
    embedder.embed.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]
    store = MagicMock()
    store.get.return_value = []

    n = _store_file(_pending(elements=["e1"]), "b", chunker, embedder, store, batch_size=2)

    assert n == 5
    chunker.chunk.assert_called_once_with(["e1"], book_id="b", source_file="ch01.pdf")
    assert embedder.embed.call_count == 3
    assert store.add_chunks.call_count == 3


def test_store_file_audio_chunks_skip_chunker():
    chunk = Chunk(chunk_id="b/a.mp3/0000", book_id="b", source_file="a.mp3",
                  element_type="audio", content="hi", token_count=1)
    chunker = MagicMock()
    embedder = MagicMock(); embedder.embed.return_value = [[0.1] * 1024]
    store = MagicMock()
    store.get.return_value = []

    n = _store_file(_pending(source_file="a.mp3", chunks=[chunk]),
                    "b", chunker, embedder, store, batch_size=64)

    chunker.chunk.assert_not_called()
    assert n == 1


def test_store_file_overrides_source_file_on_chunks():
    chunk = Chunk(chunk_id="b/x/0000", book_id="b", source_file="wrong.pdf",
                  element_type="text", content="hi", token_count=1)
    chunker = MagicMock(); chunker.chunk.return_value = [chunk]
    embedder = MagicMock(); embedder.embed.return_value = [[0.1] * 1024]
    store = MagicMock()
    store.get.return_value = []

    _store_file(_pending(source_file="ch01(1).pdf", elements=["e"]),
                "b", chunker, embedder, store, batch_size=64)

    assert chunk.source_file == "ch01(1).pdf"


def test_store_file_empty_chunks_returns_zero(capsys):
    chunker = MagicMock(); chunker.chunk.return_value = []
    embedder = MagicMock()

    n = _store_file(_pending(elements=["e"]), "b", chunker, embedder, MagicMock(), batch_size=64)

    assert n == 0
    embedder.embed.assert_not_called()
    assert "No chunks produced" in capsys.readouterr().out


def test_store_file_skips_already_existing_chunks():
    chunks = [
        Chunk(chunk_id=f"b/ch01.pdf/p0001/{i:04d}", book_id="b", source_file="ch01.pdf",
              element_type="text", content=f"chunk {i}", token_count=1)
        for i in range(3)
    ]
    chunker = MagicMock(); chunker.chunk.return_value = chunks
    embedder = MagicMock()
    embedder.embed.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]
    store = MagicMock()
    store.get.return_value = [{"chunk_id": chunks[0].chunk_id}, {"chunk_id": chunks[1].chunk_id}]

    n = _store_file(_pending(elements=["e1"]), "b", chunker, embedder, store, batch_size=64)

    assert n == 3  # 批次整体仍然算"处理完"，即便部分是复用的
    embedder.embed.assert_called_once_with([chunks[2].content])
    store.add_chunks.assert_called_once_with("b", [chunks[2]], [[0.1] * 1024])


def test_store_file_all_chunks_exist_skips_embed_entirely():
    chunks = [Chunk(chunk_id="b/ch01.pdf/p0001/0000", book_id="b", source_file="ch01.pdf",
                     element_type="text", content="c", token_count=1)]
    chunker = MagicMock(); chunker.chunk.return_value = chunks
    embedder = MagicMock()
    store = MagicMock()
    store.get.return_value = [{"chunk_id": chunks[0].chunk_id}]

    n = _store_file(_pending(elements=["e1"]), "b", chunker, embedder, store, batch_size=64)

    assert n == 1
    embedder.embed.assert_not_called()
    store.add_chunks.assert_not_called()


# ── run_ingest() 直接调用（不经过 argparse）─────────────────────────────────

def test_run_ingest_returns_structured_result(tmp_path):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", return_value=3):
        mock_store_cls.return_value.count.return_value = 3
        result = run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    assert result == IngestResult(
        total_chunks=3, failures=[], not_attempted=[], aborted_early=False,
    )


def test_run_ingest_uses_injected_store_instead_of_constructing_one(tmp_path):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)
    injected_store = MagicMock()
    injected_store.count.return_value = 3

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", return_value=3):
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir), store=injected_store)

    mock_store_cls.assert_not_called()


def test_run_ingest_reports_failures_without_raising(tmp_path):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", side_effect=RuntimeError("boom")):
        mock_store_cls.return_value.count.return_value = 0
        result = run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    # 直接调用 run_ingest 不会 sys.exit —— main() 才负责把失败翻译成退出码
    assert result.failures[0]["error_type"] == "RuntimeError"


# ── 阶段1 解析结果缓存接入 ──────────────────────────────────────────────

def test_run_ingest_cache_hit_skips_parse_file(tmp_path):
    from pipeline.parse import parse_cache

    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    sha = _sha256(str(f))
    parse_cache.set(str(chroma_dir), "b", sha, [Element(type="text", content="cached", page_num=1)], None)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file") as mock_parse_file, \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 1
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    mock_parse_file.assert_not_called()


def test_run_ingest_cache_miss_calls_parse_file_and_writes_cache(tmp_path):
    from pipeline.parse import parse_cache

    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    sha = _sha256(str(f))
    elem = Element(type="text", content="fresh", page_num=1)

    # _store_file 抛错让阶段3失败——失败不是缓存的清理触发点（清理只发生在
    # 成功入库、提交时排除、删书三种终态），条目留存，正是失败重试要复用的
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)) as mock_parse_file, \
         patch("scripts.ingest._store_file", side_effect=RuntimeError("boom")):
        mock_store_cls.return_value.count.return_value = 0
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    mock_parse_file.assert_called_once()
    cached_elements, _ = parse_cache.get(str(chroma_dir), "b", sha)
    assert cached_elements == [elem]


def test_run_ingest_resizes_figure_bytes_before_caching(tmp_path):
    from pipeline.parse import parse_cache

    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    sha = _sha256(str(f))
    fig = Element(type="figure", content="![]()", page_num=1,
                  metadata={"image_bytes": b"raw-bytes"})

    # 同上：阶段3失败不触发清理，缓存条目留存，可以断言里面存的是缩放后字节
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([fig], None)), \
         patch("scripts.ingest._resize_to_limit", side_effect=lambda b: b + b"-resized") as mock_resize, \
         patch("scripts.ingest._store_file", side_effect=RuntimeError("boom")):
        mock_store_cls.return_value.count.return_value = 0
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    mock_resize.assert_called_once_with(b"raw-bytes")
    cached_elements, _ = parse_cache.get(str(chroma_dir), "b", sha)
    assert cached_elements[0].metadata["image_bytes"] == b"raw-bytes-resized"


# ── 文件完整入库后清理缓存 ──────────────────────────────────────────────

def test_run_ingest_cleans_up_caches_after_successful_commit(tmp_path):
    from pipeline.parse import parse_cache, vlm_cache

    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    sha = _sha256(str(f))
    fig = Element(type="figure", content="![]()", page_num=1,
                  metadata={"image_bytes": b"resized-bytes"})
    image_sha = hashlib.sha256(b"resized-bytes").hexdigest()

    parse_cache.set(str(chroma_dir), "b", sha, [fig], None)
    vlm_cache.set(str(chroma_dir), "b", image_sha, "some description")

    def fake_resolve(files_elements, **kwargs):
        # 模拟真实阶段2：描述完成、标记状态、弹出字节——
        # 否则图片会命中"未描述完"签名，阶段3拒绝入库
        for elements in files_elements:
            for elem in elements:
                elem.metadata["vlm_status"] = "described"
                elem.metadata.pop("image_bytes", None)
        return MagicMock(described=1, degraded=0, no_bytes=0, breaker_tripped=False)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", side_effect=fake_resolve), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 1
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    assert parse_cache.get(str(chroma_dir), "b", sha) is None
    assert vlm_cache.get(str(chroma_dir), "b", image_sha) is None


def test_run_ingest_does_not_clean_caches_on_failure(tmp_path):
    from pipeline.parse import parse_cache

    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    sha = _sha256(str(f))
    elem = Element(type="text", content="x", page_num=1)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", side_effect=RuntimeError("boom")):
        mock_store_cls.return_value.count.return_value = 0
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    # 阶段1 解析后写了缓存，阶段3 失败——缓存条目必须还在，下次重跑省掉重新解析
    assert parse_cache.get(str(chroma_dir), "b", sha) is not None


# ── should_pause 贯穿 ────────────────────────────────────────────────────

def test_run_ingest_pause_stops_before_next_file(tmp_path):
    f1 = tmp_path / "ch01.pdf"; f1.write_bytes(b"one")
    f2 = tmp_path / "ch02.pdf"; f2.write_bytes(b"two")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)
    pause_after_first = []

    def should_pause():
        return len(pause_after_first) > 0

    def fake_parse(file_path, *a, **k):
        pause_after_first.append(file_path)  # 第一个文件解析完之后才开始返回 True
        return ([elem], None)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", side_effect=fake_parse), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 1
        result = run_ingest("b", [str(f1), str(f2)], chroma_dir=str(chroma_dir),
                            should_pause=should_pause)

    assert pause_after_first == [str(f1)]  # f2 从未被解析
    assert result.not_attempted == [str(f2)]
    assert result.aborted_early is True


def test_run_ingest_pause_not_checked_mid_stage3(tmp_path):
    """阶段3不检查暂停——should_pause 在第2个文件开始前才变 True，
    但第1个文件已经在阶段1 通过、进了 pending，阶段3 会把它完整跑完，
    不会因为 should_pause 已经变 True 而被腰斩。"""
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    f2 = tmp_path / "ch02.pdf"; f2.write_bytes(b"two")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)
    call_count = []

    def fake_pause():
        call_count.append(1)
        return len(call_count) > 1  # 第2个文件开始前才暂停

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", return_value=1) as mock_store_file:
        mock_store_cls.return_value.count.return_value = 1
        result = run_ingest("b", [str(f), str(f2)], chroma_dir=str(chroma_dir),
                            should_pause=fake_pause)

    # 只有第一个文件解析进了 pending 并走完阶段3——阶段3 本身不查 should_pause，
    # 已经进 pending 的那一个文件完整跑完，没有被"腰斩"。
    mock_store_file.assert_called_once()
    assert result.not_attempted == [str(f2)]


def test_run_ingest_audio_paused_mid_file_treated_as_not_attempted(tmp_path):
    from scripts.ingest import AudioParsePaused

    f1 = tmp_path / "a.mp3"; f1.write_bytes(b"one")
    f2 = tmp_path / "b.mp3"; f2.write_bytes(b"two")
    chroma_dir = tmp_path / "chroma"

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", side_effect=AudioParsePaused("killed")), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 0
        result = run_ingest("b", [str(f1), str(f2)], chroma_dir=str(chroma_dir))

    # AudioParsePaused 不是"失败"——不进 failures，整批从这个文件开始都算 not_attempted
    assert result.failures == []
    assert result.not_attempted == [str(f1), str(f2)]
    assert result.aborted_early is True


def test_run_ingest_default_should_pause_never_stops(tmp_path):
    """不传 should_pause 时（比如现有 CLI 用法）行为完全不变。"""
    f1 = tmp_path / "ch01.pdf"; f1.write_bytes(b"one")
    f2 = tmp_path / "ch02.pdf"; f2.write_bytes(b"two")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", return_value=1) as mock_store_file:
        mock_store_cls.return_value.count.return_value = 2
        result = run_ingest("b", [str(f1), str(f2)], chroma_dir=str(chroma_dir))

    assert mock_store_file.call_count == 2
    assert result.not_attempted == []
    assert result.aborted_early is False


# ── on_progress 回调 ─────────────────────────────────────────────────────

def test_run_ingest_reports_parsing_progress_per_file(tmp_path):
    f1 = tmp_path / "ch01.pdf"; f1.write_bytes(b"one")
    f2 = tmp_path / "ch02.pdf"; f2.write_bytes(b"two")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)
    updates = []

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 2
        run_ingest("b", [str(f1), str(f2)], chroma_dir=str(chroma_dir),
                   on_progress=updates.append)

    parsing_updates = [u for u in updates if u.stage == "parsing"]
    assert [(u.current_file, u.total_files) for u in parsing_updates] == [(1, 2), (2, 2)]
    assert [u.current_filename for u in parsing_updates] == ["ch01.pdf", "ch02.pdf"]
    assert all(u.current_image is None for u in parsing_updates)


def test_run_ingest_reports_vlm_progress_with_frozen_file_counts(tmp_path):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    chroma_dir = tmp_path / "chroma"
    fig = Element(type="figure", content="![]()", page_num=1, metadata={"image_bytes": b"x"})
    updates = []

    def fake_resolve(files_elements, chroma_dir=None, book_id=None, should_pause=None, on_progress=None):
        on_progress(1, 3)
        on_progress(2, 3)
        return MagicMock(described=2, degraded=0, no_bytes=0, breaker_tripped=False)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", side_effect=fake_resolve), \
         patch("scripts.ingest._parse_file", return_value=([fig], None)), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 1
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir), on_progress=updates.append)

    vlm_updates = [u for u in updates if u.stage == "vlm"]
    assert [(u.current_image, u.total_images) for u in vlm_updates] == [(1, 3), (2, 3)]
    assert all((u.current_file, u.total_files) == (1, 1) for u in vlm_updates)  # 阶段1只有1个文件成功解析


def test_run_ingest_reports_storing_stage_without_counts(tmp_path):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)
    updates = []

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 1
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir), on_progress=updates.append)

    storing_updates = [u for u in updates if u.stage == "storing"]
    assert len(storing_updates) == 1
    u = storing_updates[0]
    assert (u.current_file, u.total_files, u.current_image, u.total_images) == (None, None, None, None)


def test_run_ingest_default_on_progress_is_noop(tmp_path):
    """不传 on_progress 时（比如现有 CLI 用法）不应该报错。"""
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 1
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))  # 不传 on_progress，不应抛异常


# ── on_file_committed 回调 ──────────────────────────────────────────────

def test_run_ingest_on_file_committed_fires_after_successful_store(tmp_path):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)
    committed = []

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_store_cls.return_value.count.return_value = 1
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir),
                   on_file_committed=committed.append)

    assert committed == [str(f)]


def test_run_ingest_on_file_committed_fires_for_already_ingested_skip(tmp_path):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    sha = _sha256(str(f))
    _save_manifest(str(chroma_dir / ".manifests"), "b", {"sha256_to_file": {sha: "ch01.pdf"}})
    committed = []

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest._parse_file") as mock_parse_file:
        mock_store_cls.return_value.count.return_value = 0
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir),
                   on_file_committed=committed.append)

    mock_parse_file.assert_not_called()
    assert committed == [str(f)]  # 跳过 == 早已完成，同样要通知


def test_run_ingest_on_file_committed_not_fired_on_failure(tmp_path):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    chroma_dir = tmp_path / "chroma"
    elem = Element(type="text", content="x", page_num=1)
    committed = []

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([elem], None)), \
         patch("scripts.ingest._store_file", side_effect=RuntimeError("boom")):
        mock_store_cls.return_value.count.return_value = 0
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir),
                   on_file_committed=committed.append)

    assert committed == []


# ── 阶段2被暂停打断的文件，阶段3拒绝入库 ────────────────────────────────

def test_run_ingest_all_files_paused_reports_no_storing_stage(tmp_path):
    """一批里所有文件都因暂停未描述完图片时，不该播报 stage=\"storing\"——
    过滤发生在阶段3循环之前，进入循环的 pending 已经是空的。"""
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    chroma_dir = tmp_path / "chroma"
    fig = Element(type="figure", content="![](x.png)", page_num=1,
                  metadata={"image_bytes": b"img"})
    updates = []

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([fig], None)), \
         patch("scripts.ingest._store_file") as mock_store_file:
        mock_store_cls.return_value.count.return_value = 0
        run_ingest("b", [str(f)], chroma_dir=str(chroma_dir), on_progress=updates.append)

    mock_store_file.assert_not_called()
    assert [u for u in updates if u.stage == "storing"] == []


def test_run_ingest_stage2_paused_file_not_committed(tmp_path):
    """暂停打在阶段2：图片没描述完的文件不入库、不记 manifest、缓存保留、
    归 not_attempted，on_file_committed 不触发。"""
    from pipeline.parse import parse_cache

    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    chroma_dir = tmp_path / "chroma"
    sha = _sha256(str(f))
    # 阶段2被暂停跳过的签名：image_bytes 还在、无 vlm_status
    fig = Element(type="figure", content="![](x.png)", page_num=1,
                  metadata={"image_bytes": b"img"})
    committed = []

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([fig], None)), \
         patch("scripts.ingest._store_file", return_value=5) as mock_store_file:
        mock_store_cls.return_value.count.return_value = 0
        result = run_ingest("b", [str(f)], chroma_dir=str(chroma_dir),
                            on_file_committed=committed.append)

    mock_store_file.assert_not_called()
    assert committed == []
    manifest = _load_manifest(str(chroma_dir / ".manifests"), "b")
    assert sha not in manifest["sha256_to_file"]
    assert parse_cache.get(str(chroma_dir), "b", sha) is not None  # 缓存保留，恢复后续跑
    assert result.failures == []
    assert result.not_attempted == [str(f)]
    assert result.aborted_early is True


def test_run_ingest_stage2_pause_commits_fully_described_files(tmp_path):
    """同一批里图片已全部描述完的文件照常入库——阶段3"跑完这一批"的本意。"""
    f1 = tmp_path / "ch01.pdf"; f1.write_bytes(b"one")
    f2 = tmp_path / "ch02.pdf"; f2.write_bytes(b"two")
    chroma_dir = tmp_path / "chroma"
    done_fig = Element(type="figure", content="a diagram of X", page_num=1,
                       metadata={"vlm_status": "described"})  # 字节已弹出
    paused_fig = Element(type="figure", content="![](x.png)", page_num=1,
                         metadata={"image_bytes": b"img"})
    committed = []

    def fake_parse(file_path, *a, **k):
        if file_path == str(f1):
            return ([done_fig], None)
        return ([paused_fig], None)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=1, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", side_effect=fake_parse), \
         patch("scripts.ingest._store_file", return_value=3) as mock_store_file:
        mock_store_cls.return_value.count.return_value = 3
        result = run_ingest("b", [str(f1), str(f2)], chroma_dir=str(chroma_dir),
                            on_file_committed=committed.append)

    mock_store_file.assert_called_once()  # 只有 f1 入库
    assert committed == [str(f1)]
    manifest = _load_manifest(str(chroma_dir / ".manifests"), "b")
    assert _sha256(str(f1)) in manifest["sha256_to_file"]
    assert _sha256(str(f2)) not in manifest["sha256_to_file"]
    assert result.not_attempted == [str(f2)]


def test_run_ingest_breaker_degraded_file_still_commits(tmp_path):
    """熔断降级语义不变：vlm_status='degraded'、字节已弹出——照常入库。"""
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    chroma_dir = tmp_path / "chroma"
    degraded_fig = Element(type="figure", content="![](x.png)", page_num=1,
                           metadata={"vlm_status": "degraded"})

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=1, no_bytes=0, breaker_tripped=True)), \
         patch("scripts.ingest._parse_file", return_value=([degraded_fig], None)), \
         patch("scripts.ingest._store_file", return_value=2) as mock_store_file:
        mock_store_cls.return_value.count.return_value = 2
        result = run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    mock_store_file.assert_called_once()
    manifest = _load_manifest(str(chroma_dir / ".manifests"), "b")
    assert _sha256(str(f)) in manifest["sha256_to_file"]
    assert result.failures == []
    assert result.not_attempted == []


def test_run_ingest_standalone_image_paused_not_a_failure(tmp_path):
    """独立图片被暂停打断：归 not_attempted（被打断），不是 failures（失败），不回滚。"""
    f = tmp_path / "fig.png"; f.write_bytes(b"\x89PNG fake")
    chroma_dir = tmp_path / "chroma"
    fig = Element(type="figure", content="![](fig.png)", page_num=0,
                  metadata={"image_bytes": b"img"})

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([fig], None)), \
         patch("scripts.ingest._store_file") as mock_store_file:
        mock_store = mock_store_cls.return_value
        mock_store.count.return_value = 0
        result = run_ingest("b", [str(f)], chroma_dir=str(chroma_dir))

    mock_store_file.assert_not_called()
    mock_store.delete_by_source.assert_not_called()
    assert result.failures == []
    assert result.not_attempted == [str(f)]
    assert result.aborted_early is True


def test_main_no_files_in_dir_returns_early(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ingest.py", "--book-id", "b", "--dir", str(tmp_path)])
    with patch("scripts.ingest.ChromaStore") as mock_store_cls:
        main()
    mock_store_cls.assert_not_called()
    assert "No files found." in capsys.readouterr().out


def test_main_skips_already_ingested_file(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    manifest_dir = chroma_dir / ".manifests"
    sha = _sha256(str(f))
    _save_manifest(str(manifest_dir), "b", {"sha256_to_file": {sha: "ch01.pdf"}})

    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--file", str(f), "--chroma-dir", str(chroma_dir),
    ])
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest._parse_file") as mock_parse_file:
        mock_store_cls.return_value.count.return_value = 0
        main()

    mock_parse_file.assert_not_called()


def test_main_success_writes_manifest_and_empty_failures_json(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"

    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--file", str(f), "--chroma-dir", str(chroma_dir),
    ])
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([Element(type="text", content="x", page_num=1)], None)), \
         patch("scripts.ingest._store_file", return_value=3):
        mock_store_cls.return_value.count.return_value = 3
        main()

    manifest = _load_manifest(str(chroma_dir / ".manifests"), "b")
    assert manifest["sha256_to_file"][_sha256(str(f))] == "ch01.pdf"

    failures_data = json.loads((chroma_dir / ".manifests" / "b.failures.json").read_text())
    assert failures_data["failures"] == []
    assert failures_data["aborted_early"] is False
    assert failures_data["not_attempted"] == []


def test_main_one_file_fails_others_continue_and_exits_nonzero(tmp_path, monkeypatch, capsys):
    f1 = tmp_path / "ch01.pdf"; f1.write_bytes(b"one")
    f2 = tmp_path / "ch02.pdf"; f2.write_bytes(b"two")
    chroma_dir = tmp_path / "chroma"

    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--dir", str(tmp_path), "--chroma-dir", str(chroma_dir),
    ])

    def fake_parse(file_path, *args, **kwargs):
        if file_path == str(f1):
            raise RuntimeError("boom")
        return ([Element(type="text", content="x", page_num=1)], None)

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", side_effect=fake_parse), \
         patch("scripts.ingest._store_file", return_value=5):
        mock_store_cls.return_value.count.return_value = 5
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1

    manifest = _load_manifest(str(chroma_dir / ".manifests"), "b")
    assert _sha256(str(f1)) not in manifest["sha256_to_file"]
    assert manifest["sha256_to_file"][_sha256(str(f2))] == "ch02.pdf"

    failures_data = json.loads((chroma_dir / ".manifests" / "b.failures.json").read_text())
    assert len(failures_data["failures"]) == 1
    assert failures_data["failures"][0]["file"] == str(f1)
    assert failures_data["failures"][0]["error_type"] == "RuntimeError"
    assert failures_data["aborted_early"] is False

    assert "Failed to ingest" in capsys.readouterr().out


def test_main_failure_rolls_back_chroma_data(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--file", str(f), "--chroma-dir", str(chroma_dir),
    ])
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([Element(type="text", content="x", page_num=1)], None)), \
         patch("scripts.ingest._store_file", side_effect=RuntimeError("boom")):
        mock_store = mock_store_cls.return_value
        mock_store.count.return_value = 0
        with pytest.raises(SystemExit):
            main()

    mock_store.delete_by_source.assert_called_once_with("b", "ch01.pdf")


def test_main_rollback_failure_does_not_crash_batch(tmp_path, monkeypatch):
    f1 = tmp_path / "ch01.pdf"; f1.write_bytes(b"one")
    f2 = tmp_path / "ch02.pdf"; f2.write_bytes(b"two")
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--dir", str(tmp_path), "--chroma-dir", str(chroma_dir),
    ])

    def fake_store(pending, *args, **kwargs):
        if Path(pending.file_path).name == "ch01.pdf":
            raise RuntimeError("boom")
        return 5

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([Element(type="text", content="x", page_num=1)], None)), \
         patch("scripts.ingest._store_file", side_effect=fake_store):
        mock_store = mock_store_cls.return_value
        mock_store.count.return_value = 5
        mock_store.delete_by_source.side_effect = RuntimeError("cleanup also broken")
        with pytest.raises(SystemExit):
            main()

    manifest = _load_manifest(str(chroma_dir / ".manifests"), "b")
    assert manifest["sha256_to_file"][_sha256(str(f2))] == "ch02.pdf"


def test_main_success_does_not_call_rollback(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--file", str(f), "--chroma-dir", str(chroma_dir),
    ])
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock(
             described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([Element(type="text", content="x", page_num=1)], None)), \
         patch("scripts.ingest._store_file", return_value=3):
        mock_store = mock_store_cls.return_value
        mock_store.count.return_value = 3
        main()

    mock_store.delete_by_source.assert_not_called()


def test_main_skip_path_does_not_call_rollback(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    manifest_dir = chroma_dir / ".manifests"
    sha = _sha256(str(f))
    _save_manifest(str(manifest_dir), "b", {"sha256_to_file": {sha: "ch01.pdf"}})

    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--file", str(f), "--chroma-dir", str(chroma_dir),
    ])
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest._parse_file") as mock_parse_file:
        mock_store = mock_store_cls.return_value
        mock_store.count.return_value = 0
        main()

    mock_parse_file.assert_not_called()
    mock_store.delete_by_source.assert_not_called()


def test_main_circuit_breaker_resets_on_success(tmp_path, monkeypatch):
    names = ["ch0.pdf", "ch1.pdf", "ch2.pdf", "ch3.pdf", "ch4.pdf"]
    for name in names:
        (tmp_path / name).write_bytes(name.encode())
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setenv("INGEST_MAX_CONSECUTIVE_FAILURES", "2")
    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--dir", str(tmp_path), "--chroma-dir", str(chroma_dir),
    ])

    # ch0 fail, ch1 succeed, ch2/ch3/ch4 succeed parse:
    # ch0 fails in parse (count 1) → ch1 succeeds (reset) → ch2 fails store
    # (count 1) → ch3 fails store (count 2 → abort) → ch4 not attempted
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock()), \
         patch("scripts.ingest._parse_file", side_effect=[
             RuntimeError("boom"),  # ch0.pdf — parse 失败释放
             ([Element(type="text", content="x", page_num=1)], None),     # ch1.pdf — 成功
             ([Element(type="text", content="x", page_num=1)], None),     # ch2.pdf — 成功
             ([Element(type="text", content="x", page_num=1)], None),     # ch3.pdf — 成功
             ([Element(type="text", content="x", page_num=1)], None),     # ch4.pdf — 成功但不会进 store
         ]), \
         patch("scripts.ingest._store_file", side_effect=[
             1,                     # ch1.pdf — 成功，consecutive_failures 重置
             RuntimeError("boom"), # ch2.pdf — 失败 (count 1)
             RuntimeError("boom"), # ch3.pdf — 失败 (count 2, 触发熔断，ch4 跳过)
         ]):
        mock_store_cls.return_value.count.return_value = 1
        with pytest.raises(SystemExit):
            main()

    failures_data = json.loads((chroma_dir / ".manifests" / "b.failures.json").read_text())
    failed_names = [Path(f["file"]).name for f in failures_data["failures"]]
    # ch0 parse 失败(计数1) → ch1 store 成功(重置为0) → ch2 store 失败(计数1)
    # → ch3 store 失败(计数2, 达到阈值中止) → ch4 store 跳过了
    assert failed_names == ["ch0.pdf", "ch2.pdf", "ch3.pdf"]
    assert failures_data["aborted_early"] is True
    assert [Path(p).name for p in failures_data["not_attempted"]] == ["ch4.pdf"]


def test_main_circuit_breaker_disabled_by_default_processes_all(tmp_path, monkeypatch):
    for i in range(4):
        (tmp_path / f"ch{i}.pdf").write_bytes(f"content{i}".encode())
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--dir", str(tmp_path), "--chroma-dir", str(chroma_dir),
    ])

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures", return_value=MagicMock()), \
         patch("scripts.ingest._parse_file", side_effect=[
             RuntimeError("boom"), RuntimeError("boom"),
             RuntimeError("boom"), RuntimeError("boom"),
         ]), \
         patch("scripts.ingest._store_file"):
        mock_store_cls.return_value.count.return_value = 0
        with pytest.raises(SystemExit):
            main()

    failures_data = json.loads((chroma_dir / ".manifests" / "b.failures.json").read_text())
    assert failures_data["aborted_early"] is False
    assert len(failures_data["failures"]) == 4
    assert failures_data["not_attempted"] == []


# ── 三阶段架构专属用例 ───────────────────────────────────────────────────────

def test_main_standalone_image_vlm_failure_marks_file_failed(tmp_path, monkeypatch):
    f = tmp_path / "fig.png"
    f.write_bytes(b"\x89PNG fake")
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--file", str(f), "--chroma-dir", str(chroma_dir),
    ])
    degraded_elem = MagicMock()
    degraded_elem.type = "figure"
    degraded_elem.metadata = {"vlm_status": "degraded"}

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.resolve_figures"), \
         patch("scripts.ingest._parse_file", return_value=([degraded_elem], None)), \
         patch("scripts.ingest._store_file") as mock_store_file:
        mock_store_cls.return_value.count.return_value = 0
        with pytest.raises(SystemExit):
            main()

    mock_store_file.assert_not_called()
    failures_data = json.loads((chroma_dir / ".manifests" / "b.failures.json").read_text())
    assert len(failures_data["failures"]) == 1


def test_main_releases_marker_before_vlm_batch(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--file", str(f), "--chroma-dir", str(chroma_dir),
    ])
    call_order = []

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest.MarkerParser") as mock_marker_cls, \
         patch("scripts.ingest.resolve_figures",
               side_effect=lambda *a, **k: call_order.append("vlm") or MagicMock(
                   described=0, degraded=0, no_bytes=0, breaker_tripped=False)), \
         patch("scripts.ingest._parse_file", return_value=([Element(type="text", content="x", page_num=1)], None)), \
         patch("scripts.ingest._store_file", return_value=1):
        mock_marker_cls.release_models.side_effect = lambda: call_order.append("release")
        mock_store_cls.return_value.count.return_value = 1
        main()

    assert call_order == ["release", "vlm"]
