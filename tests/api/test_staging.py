from pathlib import Path

from pipeline.api import staging


def test_list_files_empty_when_no_file(tmp_path):
    assert staging.list_files(str(tmp_path), "b") == []


def test_add_file_then_list_roundtrips(tmp_path):
    files = staging.add_file(str(tmp_path), "b", "/data/ch01.pdf")
    assert files == ["/data/ch01.pdf"]
    assert staging.list_files(str(tmp_path), "b") == ["/data/ch01.pdf"]


def test_add_file_dedupes(tmp_path):
    staging.add_file(str(tmp_path), "b", "/data/ch01.pdf")
    files = staging.add_file(str(tmp_path), "b", "/data/ch01.pdf")
    assert files == ["/data/ch01.pdf"]


def test_add_file_preserves_order(tmp_path):
    staging.add_file(str(tmp_path), "b", "/data/ch02.pdf")
    staging.add_file(str(tmp_path), "b", "/data/ch01.pdf")
    assert staging.list_files(str(tmp_path), "b") == ["/data/ch02.pdf", "/data/ch01.pdf"]


def test_remove_file_returns_true_and_removes(tmp_path):
    staging.add_file(str(tmp_path), "b", "/data/ch01.pdf")
    staging.add_file(str(tmp_path), "b", "/data/ch02.pdf")

    assert staging.remove_file(str(tmp_path), "b", "/data/ch01.pdf") is True
    assert staging.list_files(str(tmp_path), "b") == ["/data/ch02.pdf"]


def test_remove_missing_file_returns_false(tmp_path):
    assert staging.remove_file(str(tmp_path), "b", "/data/nope.pdf") is False


def test_delete_list_removes_persisted_file(tmp_path):
    staging.add_file(str(tmp_path), "b", "/data/ch01.pdf")
    staging.delete_list(str(tmp_path), "b")
    assert staging.list_files(str(tmp_path), "b") == []
    assert not (tmp_path / ".manifests" / "b.pending_files.json").exists()


def test_delete_list_missing_is_noop(tmp_path):
    staging.delete_list(str(tmp_path), "b")  # 不应抛异常


def test_different_books_are_independent(tmp_path):
    staging.add_file(str(tmp_path), "book-a", "/data/a.pdf")
    assert staging.list_files(str(tmp_path), "book-b") == []


def test_corrupted_file_degrades_to_empty(tmp_path):
    p = tmp_path / ".manifests" / "b.pending_files.json"
    p.parent.mkdir(parents=True)
    p.write_text("{not valid json")
    assert staging.list_files(str(tmp_path), "b") == []


def test_save_uses_atomic_replace(tmp_path, monkeypatch):
    calls = []
    original_replace = Path.replace

    def spy_replace(self, target):
        calls.append((str(self), str(target)))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", spy_replace)
    staging.add_file(str(tmp_path), "b", "/data/ch01.pdf")

    assert len(calls) == 1
    assert calls[0][0].endswith(".tmp")
    assert calls[0][1].endswith("b.pending_files.json")


def test_write_failure_raises(tmp_path, monkeypatch):
    """待导入列表是正确性入口，不是缓存——写失败必须抛出去，不能静默吞掉。"""
    import pytest

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(Path, "write_text", boom)

    with pytest.raises(OSError):
        staging.add_file(str(tmp_path), "b", "/data/ch01.pdf")
