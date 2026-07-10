import hashlib
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from pipeline.api import staging
from pipeline.api.ingest_runner import ingest_processor
from pipeline.chunk.schema import Chunk
from pipeline.parse import parse_cache, vlm_cache
from pipeline.parse.base import Element
from scripts.ingest import IngestResult, ProgressUpdate, _sha256


def _ok_result():
    return IngestResult(total_chunks=3, failures=[], not_attempted=[], aborted_early=False)


def _run(tmp_path, monkeypatch, file_paths, run_ingest_side_effect, book_id="b"):
    """公共驱动：CHROMA_DIR 指向 tmp_path，mock 掉真正的 run_ingest。"""
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    progress_updates = []
    with patch("scripts.ingest.run_ingest", side_effect=run_ingest_side_effect) as mock_run:
        summary = ingest_processor(book_id, file_paths,
                                   should_pause=lambda: False,
                                   report_progress=progress_updates.append)
    return summary, mock_run, progress_updates


def test_summary_dict_built_from_ingest_result(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")

    summary, mock_run, _ = _run(tmp_path, monkeypatch, [str(f)],
                                lambda *a, **k: _ok_result())

    assert summary == {
        "book_id": "b", "total_chunks": 3, "failures": [],
        "not_attempted": [], "aborted_early": False,
    }
    call = mock_run.call_args
    assert call.args == ("b", [str(f)])
    assert call.kwargs["chroma_dir"] == str(tmp_path)


def test_progress_updates_converted_to_dicts(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")

    def fake_run(book_id, file_paths, chroma_dir, should_pause, on_progress, on_file_committed, store):
        on_progress(ProgressUpdate(stage="parsing", current_file=1, total_files=1))
        return _ok_result()

    _, _, progress_updates = _run(tmp_path, monkeypatch, [str(f)], fake_run)

    assert progress_updates == [asdict(
        ProgressUpdate(stage="parsing", current_file=1, total_files=1))]


def test_on_file_committed_removes_from_staging(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    staging.add_file(str(tmp_path), "b", str(f))

    def fake_run(book_id, file_paths, chroma_dir, should_pause, on_progress, on_file_committed, store):
        on_file_committed(str(f))
        return _ok_result()

    _run(tmp_path, monkeypatch, [str(f)], fake_run)

    assert staging.list_files(str(tmp_path), "b") == []


def test_on_file_committed_swallows_staging_errors(tmp_path, monkeypatch):
    """回调在 run_ingest 阶段3的 try 块内被调——列表写失败绝不能抛出去，
    否则一个已成功入库的文件会被误判失败并回滚（manifest 已写入，状态不一致）。"""
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")

    def boom_remove(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr("pipeline.api.ingest_runner.staging.remove_file", boom_remove)

    def fake_run(book_id, file_paths, chroma_dir, should_pause, on_progress, on_file_committed, store):
        on_file_committed(str(f))  # 不应抛异常
        return _ok_result()

    summary, _, _ = _run(tmp_path, monkeypatch, [str(f)], fake_run)
    assert summary["total_chunks"] == 3


def test_submission_purges_cache_of_excluded_files(tmp_path, monkeypatch):
    """spec 第4节触发点2：上次未完成处理涉及的文件，这次提交不包含它 → 清它的缓存。"""
    included = tmp_path / "keep.pdf"; included.write_bytes(b"keep")
    excluded = tmp_path / "drop.pdf"; excluded.write_bytes(b"drop")
    sha_keep = _sha256(str(included))
    sha_drop = _sha256(str(excluded))

    fig_bytes = b"drop-figure-bytes"
    fig = Element(type="figure", content="![]()", page_num=1,
                  metadata={"image_bytes": fig_bytes})
    image_sha = hashlib.sha256(fig_bytes).hexdigest()

    parse_cache.set(str(tmp_path), "b", sha_keep, [Element(type="text", content="k", page_num=1)], None)
    parse_cache.set(str(tmp_path), "b", sha_drop, [fig], None)
    vlm_cache.set(str(tmp_path), "b", image_sha, "desc of dropped figure")

    _run(tmp_path, monkeypatch, [str(included)], lambda *a, **k: _ok_result())

    assert parse_cache.get(str(tmp_path), "b", sha_keep) is not None   # 提交里有的：留
    assert parse_cache.get(str(tmp_path), "b", sha_drop) is None       # 被排除的：清
    assert vlm_cache.get(str(tmp_path), "b", image_sha) is None        # 连它的图片描述一起清


def test_purge_skips_unreadable_submitted_files(tmp_path, monkeypatch):
    """提交列表里的文件已从磁盘消失：算不出 sha，不参与 keep 集合，
    purge 不崩——这个文件的失败由 run_ingest 阶段1记录，不归这里管。"""
    ghost = str(tmp_path / "gone.pdf")  # 从未创建

    summary, mock_run, _ = _run(tmp_path, monkeypatch, [ghost],
                                lambda *a, **k: _ok_result())

    mock_run.assert_called_once()  # purge 没崩，run_ingest 照常被调


def test_releases_gpu_embedder_after_successful_import(tmp_path, monkeypatch):
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    release_spy = MagicMock()
    monkeypatch.setattr("pipeline.api.ingest_runner.release_gpu_model", release_spy)

    _run(tmp_path, monkeypatch, [str(f)], lambda *a, **k: _ok_result())

    release_spy.assert_called_once()


def test_releases_gpu_embedder_even_when_run_ingest_raises(tmp_path, monkeypatch):
    # 任务结束不只是"成功"这一种——run_ingest 抛异常时也不能把显存一直占着，
    # 不然一次失败的导入就会让后续每次导入都被迫跟 Ollama 抢显存。
    f = tmp_path / "ch01.pdf"; f.write_bytes(b"one")
    release_spy = MagicMock()
    monkeypatch.setattr("pipeline.api.ingest_runner.release_gpu_model", release_spy)

    def boom(*a, **k):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        _run(tmp_path, monkeypatch, [str(f)], boom)

    release_spy.assert_called_once()


def test_audio_chunks_cache_entry_purged_without_error(tmp_path, monkeypatch):
    """被排除的音频文件：缓存条目是 chunks（elements 为 None），purge 不崩。"""
    excluded = tmp_path / "drop.mp3"; excluded.write_bytes(b"audio")
    sha_drop = _sha256(str(excluded))
    chunk = Chunk(chunk_id="b/drop.mp3/0000", book_id="b", source_file="drop.mp3",
                  element_type="audio", content="hi", token_count=1)
    parse_cache.set(str(tmp_path), "b", sha_drop, None, [chunk])

    included = tmp_path / "keep.pdf"; included.write_bytes(b"keep")
    _run(tmp_path, monkeypatch, [str(included)], lambda *a, **k: _ok_result())

    assert parse_cache.get(str(tmp_path), "b", sha_drop) is None
