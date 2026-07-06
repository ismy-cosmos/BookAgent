import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from pipeline.chunk.schema import Chunk
from scripts.ingest import (
    _sha256,
    _load_manifest,
    _save_manifest,
    _resolve_source_file,
    _collect_files,
    _route_parser,
    _ingest_file,
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


def test_ingest_file_audio_uses_parse_to_chunks(tmp_path):
    f = tmp_path / "lecture.mp3"
    f.write_bytes(b"fake audio")
    chunk = Chunk(
        chunk_id="b/lecture.mp3/0000", book_id="b", source_file="lecture.mp3",
        element_type="audio", content="hello", token_count=1,
    )
    mock_parser = MagicMock()
    mock_parser.parse_to_chunks.return_value = [chunk]
    chunker = MagicMock()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 1024]
    store = MagicMock()

    with patch("scripts.ingest.AudioParser", return_value=mock_parser):
        n = _ingest_file(str(f), "b", "lecture.mp3", chunker, embedder, store, batch_size=64)

    mock_parser.parse_to_chunks.assert_called_once_with(str(f), "b", source_file="lecture.mp3")
    chunker.chunk.assert_not_called()
    assert n == 1
    store.add_chunks.assert_called_once()


def test_ingest_file_non_audio_uses_route_parser_and_chunker(tmp_path):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"fake pdf")
    chunk = Chunk(
        chunk_id="b/ch01.pdf/p0001/0000", book_id="b", source_file="ch01.pdf",
        element_type="text", content="hello", token_count=1,
    )
    mock_parser = MagicMock()
    mock_parser.parse.return_value = ["element1"]
    chunker = MagicMock()
    chunker.chunk.return_value = [chunk]
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 1024]
    store = MagicMock()

    with patch("scripts.ingest._route_parser", return_value=mock_parser) as mock_route:
        n = _ingest_file(str(f), "b", "ch01.pdf", chunker, embedder, store, batch_size=64)

    mock_route.assert_called_once_with(str(f))
    mock_parser.parse.assert_called_once_with(str(f))
    chunker.chunk.assert_called_once_with(["element1"], book_id="b", source_file="ch01.pdf")
    assert n == 1


def test_ingest_file_empty_chunks_returns_zero(tmp_path, capsys):
    f = tmp_path / "empty.pdf"
    f.write_bytes(b"fake pdf")
    mock_parser = MagicMock()
    mock_parser.parse.return_value = []
    chunker = MagicMock()
    chunker.chunk.return_value = []
    embedder = MagicMock()
    store = MagicMock()

    with patch("scripts.ingest._route_parser", return_value=mock_parser):
        n = _ingest_file(str(f), "b", "empty.pdf", chunker, embedder, store, batch_size=64)

    assert n == 0
    embedder.embed.assert_not_called()
    store.add_chunks.assert_not_called()
    assert "No chunks produced" in capsys.readouterr().out


def test_ingest_file_overrides_source_file_on_chunks(tmp_path):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"fake pdf")
    chunk = Chunk(
        chunk_id="b/ch01.pdf/p0001/0000", book_id="b", source_file="wrong-name.pdf",
        element_type="text", content="hello", token_count=1,
    )
    mock_parser = MagicMock()
    mock_parser.parse.return_value = ["element1"]
    chunker = MagicMock()
    chunker.chunk.return_value = [chunk]
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1] * 1024]
    store = MagicMock()

    with patch("scripts.ingest._route_parser", return_value=mock_parser):
        _ingest_file(str(f), "b", "ch01(1).pdf", chunker, embedder, store, batch_size=64)

    assert chunk.source_file == "ch01(1).pdf"


def test_ingest_file_batches_embed_and_store_calls(tmp_path):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"fake pdf")
    chunks = [
        Chunk(chunk_id=f"b/ch01.pdf/p0001/{i:04d}", book_id="b", source_file="ch01.pdf",
              element_type="text", content=f"chunk {i}", token_count=1)
        for i in range(5)
    ]
    mock_parser = MagicMock()
    mock_parser.parse.return_value = ["element1"]
    chunker = MagicMock()
    chunker.chunk.return_value = chunks
    embedder = MagicMock()
    embedder.embed.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]
    store = MagicMock()

    with patch("scripts.ingest._route_parser", return_value=mock_parser):
        n = _ingest_file(str(f), "b", "ch01.pdf", chunker, embedder, store, batch_size=2)

    assert n == 5
    assert embedder.embed.call_count == 3  # batch 大小 2：2+2+1
    assert store.add_chunks.call_count == 3
    first_batch = store.add_chunks.call_args_list[0].args[1]
    assert len(first_batch) == 2
    last_batch = store.add_chunks.call_args_list[2].args[1]
    assert len(last_batch) == 1


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
         patch("scripts.ingest._ingest_file") as mock_ingest_file:
        mock_store_cls.return_value.count.return_value = 0
        main()

    mock_ingest_file.assert_not_called()


def test_main_success_writes_manifest_and_empty_failures_json(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    chroma_dir = tmp_path / "chroma"

    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--file", str(f), "--chroma-dir", str(chroma_dir),
    ])
    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest._ingest_file", return_value=3):
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

    def fake_ingest_file(file_path, *args, **kwargs):
        if file_path == str(f1):
            raise RuntimeError("boom")
        return 5

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest._ingest_file", side_effect=fake_ingest_file):
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
         patch("scripts.ingest._ingest_file", side_effect=RuntimeError("boom")):
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

    def fake_ingest_file(file_path, *args, **kwargs):
        if file_path == str(f1):
            raise RuntimeError("boom")
        return 5

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest._ingest_file", side_effect=fake_ingest_file):
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
         patch("scripts.ingest._ingest_file", return_value=3):
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
         patch("scripts.ingest._ingest_file") as mock_ingest_file:
        mock_store = mock_store_cls.return_value
        mock_store.count.return_value = 0
        main()

    mock_ingest_file.assert_not_called()
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

    def fake_ingest_file(file_path, *args, **kwargs):
        if Path(file_path).name == "ch1.pdf":
            return 1
        raise RuntimeError("boom")

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest._ingest_file", side_effect=fake_ingest_file):
        mock_store_cls.return_value.count.return_value = 1
        with pytest.raises(SystemExit):
            main()

    failures_data = json.loads((chroma_dir / ".manifests" / "b.failures.json").read_text())
    failed_names = [Path(f["file"]).name for f in failures_data["failures"]]
    # ch0 失败(计数1) -> ch1 成功(重置为0) -> ch2 失败(计数1) -> ch3 失败(计数2，达到阈值中止)
    assert failed_names == ["ch0.pdf", "ch2.pdf", "ch3.pdf"]
    assert failures_data["aborted_early"] is True
    assert [Path(p).name for p in failures_data["not_attempted"]] == ["ch4.pdf"]


def test_main_circuit_breaker_disabled_by_default_processes_all(tmp_path, monkeypatch):
    for i in range(4):
        (tmp_path / f"ch{i}.pdf").write_bytes(f"content{i}".encode())
    chroma_dir = tmp_path / "chroma"
    monkeypatch.delenv("INGEST_MAX_CONSECUTIVE_FAILURES", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "ingest.py", "--book-id", "b", "--dir", str(tmp_path), "--chroma-dir", str(chroma_dir),
    ])

    with patch("scripts.ingest.Chunker"), patch("scripts.ingest.Embedder"), \
         patch("scripts.ingest.ChromaStore") as mock_store_cls, \
         patch("scripts.ingest._ingest_file", side_effect=RuntimeError("boom")):
        mock_store_cls.return_value.count.return_value = 0
        with pytest.raises(SystemExit):
            main()

    failures_data = json.loads((chroma_dir / ".manifests" / "b.failures.json").read_text())
    assert failures_data["aborted_early"] is False
    assert len(failures_data["failures"]) == 4
    assert failures_data["not_attempted"] == []
