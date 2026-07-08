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
    mock_parser.parse_to_chunks.assert_called_once_with(str(f), "b", source_file="lecture.mp3")


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

    n = _store_file(_pending(source_file="a.mp3", chunks=[chunk]),
                    "b", chunker, embedder, store, batch_size=64)

    chunker.chunk.assert_not_called()
    assert n == 1


def test_store_file_overrides_source_file_on_chunks():
    chunk = Chunk(chunk_id="b/x/0000", book_id="b", source_file="wrong.pdf",
                  element_type="text", content="hi", token_count=1)
    chunker = MagicMock(); chunker.chunk.return_value = [chunk]
    embedder = MagicMock(); embedder.embed.return_value = [[0.1] * 1024]

    _store_file(_pending(source_file="ch01(1).pdf", elements=["e"]),
                "b", chunker, embedder, MagicMock(), batch_size=64)

    assert chunk.source_file == "ch01(1).pdf"


def test_store_file_empty_chunks_returns_zero(capsys):
    chunker = MagicMock(); chunker.chunk.return_value = []
    embedder = MagicMock()

    n = _store_file(_pending(elements=["e"]), "b", chunker, embedder, MagicMock(), batch_size=64)

    assert n == 0
    embedder.embed.assert_not_called()
    assert "No chunks produced" in capsys.readouterr().out


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
