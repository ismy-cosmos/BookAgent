import json
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
