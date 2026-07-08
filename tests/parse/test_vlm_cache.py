from pipeline.parse import vlm_cache


def test_get_missing_returns_none(tmp_path):
    assert vlm_cache.get(str(tmp_path), "b", "sha1") is None


def test_set_then_get_roundtrips(tmp_path):
    vlm_cache.set(str(tmp_path), "b", "sha1", "A diagram of X.")
    assert vlm_cache.get(str(tmp_path), "b", "sha1") == "A diagram of X."


def test_corrupted_cache_file_degrades_to_miss(tmp_path):
    cache_path = tmp_path / ".manifests" / "b.vlm_cache.json"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text("{not valid json")

    assert vlm_cache.get(str(tmp_path), "b", "sha1") is None


def test_delete_removes_entry(tmp_path):
    vlm_cache.set(str(tmp_path), "b", "sha1", "desc")
    vlm_cache.delete(str(tmp_path), "b", "sha1")
    assert vlm_cache.get(str(tmp_path), "b", "sha1") is None


def test_delete_missing_entry_is_noop(tmp_path):
    vlm_cache.delete(str(tmp_path), "b", "does-not-exist")  # 不应抛异常


def test_different_books_do_not_share_cache(tmp_path):
    vlm_cache.set(str(tmp_path), "book-a", "sha1", "desc-a")
    assert vlm_cache.get(str(tmp_path), "book-b", "sha1") is None


def test_write_failure_degrades_silently(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr("pathlib.Path.write_text", boom)

    vlm_cache.set(str(tmp_path), "b", "sha1", "desc")  # 不应抛异常

    assert "warn" in capsys.readouterr().out.lower()
