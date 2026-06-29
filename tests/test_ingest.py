import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from scripts.ingest import (
    _sha256,
    _load_manifest,
    _save_manifest,
    _resolve_source_file,
    _collect_files,
    _route_parser,
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
