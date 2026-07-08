from pipeline.chunk.schema import Chunk
from pipeline.parse import parse_cache
from pipeline.parse.base import Element


def _fig_element(img_bytes=b"\x89PNGfake"):
    return Element(type="figure", content="![]()", page_num=1,
                   metadata={"image_bytes": img_bytes, "vlm_status": "pending"})


def _text_element():
    return Element(type="text", content="hello", page_num=1, metadata={})


def _chunk():
    return Chunk(chunk_id="b/a.mp3/0000", book_id="b", source_file="a.mp3",
                 element_type="audio", content="hi", token_count=1,
                 start_sec=0.0, end_sec=1.0)


def test_get_missing_returns_none(tmp_path):
    assert parse_cache.get(str(tmp_path), "b", "deadbeef") is None


def test_set_then_get_roundtrips_elements(tmp_path):
    elements = [_text_element(), _fig_element()]
    parse_cache.set(str(tmp_path), "b", "sha1", elements, None)

    got_elements, got_chunks = parse_cache.get(str(tmp_path), "b", "sha1")

    assert got_chunks is None
    assert len(got_elements) == 2
    assert got_elements[0] == elements[0]
    assert got_elements[1].metadata["image_bytes"] == b"\x89PNGfake"
    assert got_elements[1].metadata["vlm_status"] == "pending"


def test_set_then_get_roundtrips_chunks(tmp_path):
    chunks = [_chunk()]
    parse_cache.set(str(tmp_path), "b", "sha-audio", None, chunks)

    got_elements, got_chunks = parse_cache.get(str(tmp_path), "b", "sha-audio")

    assert got_elements is None
    assert got_chunks == chunks


def test_corrupted_cache_file_degrades_to_miss(tmp_path):
    cache_path = tmp_path / ".manifests" / "b.parse_cache.json"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text("{not valid json")

    assert parse_cache.get(str(tmp_path), "b", "anything") is None


def test_delete_removes_entry(tmp_path):
    parse_cache.set(str(tmp_path), "b", "sha1", [_text_element()], None)
    parse_cache.delete(str(tmp_path), "b", "sha1")

    assert parse_cache.get(str(tmp_path), "b", "sha1") is None


def test_delete_missing_entry_is_noop(tmp_path):
    parse_cache.delete(str(tmp_path), "b", "does-not-exist")  # 不应抛异常


def test_different_books_do_not_share_cache(tmp_path):
    parse_cache.set(str(tmp_path), "book-a", "sha1", [_text_element()], None)
    assert parse_cache.get(str(tmp_path), "book-b", "sha1") is None


def test_write_failure_degrades_silently(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr("pathlib.Path.write_text", boom)

    parse_cache.set(str(tmp_path), "b", "sha1", [_text_element()], None)  # 不应抛异常

    assert "warn" in capsys.readouterr().out.lower()


def test_set_with_unserializable_elements_degrades_silently(tmp_path, capsys):
    """编码失败（比如元素不是真的 dataclass、metadata 里混进不可序列化对象）
    也必须静默退化——缓存永远不能让调用方的批次失败。"""
    from unittest.mock import MagicMock

    parse_cache.set(str(tmp_path), "b", "sha1", [MagicMock()], None)  # 不应抛异常

    assert "warn" in capsys.readouterr().out.lower()
    assert parse_cache.get(str(tmp_path), "b", "sha1") is None
