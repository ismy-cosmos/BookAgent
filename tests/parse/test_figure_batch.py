"""figure_batch.resolve_figures 单元测试——OpenAI 与模型释放全 mock。"""
from unittest.mock import patch, MagicMock

import pytest

from pipeline.parse.base import Element
from pipeline.parse.figure_batch import FigureBatchStats, resolve_figures


def _fig(content="![alt-text](x.png)", with_bytes=True):
    md = {"image_bytes": b"png-bytes"} if with_bytes else {}
    return Element(type="figure", content=content, page_num=1, metadata=md)


def _run(files_elements, describe_side_effect):
    """公共驱动：mock OpenAI 构造、describe_image、_release_model。"""
    with patch("pipeline.parse.figure_batch.OpenAI"), \
         patch("pipeline.parse.figure_batch.describe_image",
               side_effect=describe_side_effect) as mock_desc, \
         patch("pipeline.parse.figure_batch.release_model") as mock_release:
        stats = resolve_figures(files_elements, model="m", ollama_base="http://fake")
    return stats, mock_desc, mock_release


def test_described_content_replaced_and_bytes_dropped():
    fig = _fig()
    stats, _, _ = _run([[fig]], describe_side_effect=["A diagram of X."])
    assert fig.content == "[alt: alt-text] A diagram of X."
    assert fig.metadata["vlm_status"] == "described"
    assert "image_bytes" not in fig.metadata
    assert stats.described == 1


def test_empty_alt_uses_bare_description():
    fig = _fig(content="![](x.png)")
    _run([[fig]], describe_side_effect=["Bare description."])
    assert fig.content == "Bare description."


def test_caption_next_element_fed_into_prompt():
    fig = _fig()
    caption = Element(type="text", content="Figure 3.2: Process lifecycle.", page_num=1)
    _, mock_desc, _ = _run([[fig, caption]], describe_side_effect=["desc"])
    prompt = mock_desc.call_args.kwargs["prompt"]
    assert "Figure 3.2: Process lifecycle." in prompt


def test_non_caption_next_element_not_in_prompt():
    fig = _fig()
    other = Element(type="text", content="Just a normal paragraph.", page_num=1)
    _, mock_desc, _ = _run([[fig, other]], describe_side_effect=["desc"])
    prompt = mock_desc.call_args.kwargs["prompt"]
    assert "normal paragraph" not in prompt


def test_figure_without_bytes_skipped_and_counted():
    fig = _fig(with_bytes=False)
    stats, mock_desc, _ = _run([[fig]], describe_side_effect=["desc"])
    mock_desc.assert_not_called()
    assert fig.content == "![alt-text](x.png)"   # 占位符原样
    assert stats.no_bytes == 1


def test_single_failure_degrades_only_that_figure():
    f1, f2 = _fig(), _fig()
    stats, _, _ = _run([[f1], [f2]],
                       describe_side_effect=[ValueError("boom"), "ok desc"])
    assert f1.metadata["vlm_status"] == "degraded"
    assert f1.content == "![alt-text](x.png)"
    assert f2.metadata["vlm_status"] == "described"
    assert stats.degraded == 1 and stats.described == 1


def test_breaker_trips_after_3_consecutive_failures(monkeypatch):
    monkeypatch.delenv("VLM_MAX_CONSECUTIVE_FAILURES", raising=False)
    figs = [_fig() for _ in range(5)]
    stats, mock_desc, _ = _run([figs],
                               describe_side_effect=[ValueError("x")] * 3)
    # 第4、5张不再调 VLM，直接降级
    assert mock_desc.call_count == 3
    assert stats.breaker_tripped is True
    assert stats.degraded == 5
    assert all(f.metadata["vlm_status"] == "degraded" for f in figs)


def test_breaker_counter_resets_on_success(monkeypatch):
    monkeypatch.delenv("VLM_MAX_CONSECUTIVE_FAILURES", raising=False)
    figs = [_fig() for _ in range(5)]
    stats, mock_desc, _ = _run(
        [figs],
        describe_side_effect=[ValueError("x"), ValueError("x"), "ok",
                              ValueError("x"), "ok"])
    assert mock_desc.call_count == 5
    assert stats.breaker_tripped is False
    assert stats.described == 2 and stats.degraded == 3


def test_release_called_exactly_once_even_on_failures():
    figs = [_fig() for _ in range(2)]
    _, _, mock_release = _run([figs], describe_side_effect=[ValueError("x"), "ok"])
    mock_release.assert_called_once()


def test_no_targets_no_client_no_release():
    with patch("pipeline.parse.figure_batch.OpenAI") as mock_cls, \
         patch("pipeline.parse.figure_batch.release_model") as mock_release:
        stats = resolve_figures([[Element(type="text", content="t", page_num=1)]])
    mock_cls.assert_not_called()
    mock_release.assert_not_called()
    assert stats == FigureBatchStats()


# ── per_image_tokens 记录（真实 usage.prompt_tokens 回传）───────────────────

def _fake_describe_with_usage(tokens):
    def _inner(client, model, b64, prompt=None, options=None, on_usage=None):
        if on_usage is not None:
            usage = MagicMock()
            usage.prompt_tokens = tokens
            on_usage(usage)
        return "desc"
    return _inner


def test_resolve_figures_records_per_image_tokens_on_success():
    fig = _fig()
    with patch("pipeline.parse.figure_batch.OpenAI"), \
         patch("pipeline.parse.figure_batch.describe_image",
               side_effect=_fake_describe_with_usage(2772)), \
         patch("pipeline.parse.figure_batch.release_model"):
        stats = resolve_figures([[fig]], model="m", ollama_base="http://fake")

    assert stats.per_image_tokens == [2772]


def test_resolve_figures_no_token_entry_when_usage_absent():
    fig = _fig()
    stats, _, _ = _run([[fig]], describe_side_effect=["desc without usage"])
    assert stats.per_image_tokens == []


def test_resolve_figures_no_token_entry_for_failed_image():
    fig = _fig()
    stats, _, _ = _run([[fig]], describe_side_effect=[ValueError("boom")])
    assert stats.per_image_tokens == []


# ── VLM 描述缓存接入 ─────────────────────────────────────────────────────

def _run_with_cache(files_elements, describe_side_effect, chroma_dir, book_id):
    with patch("pipeline.parse.figure_batch.OpenAI"), \
         patch("pipeline.parse.figure_batch.describe_image",
               side_effect=describe_side_effect) as mock_desc, \
         patch("pipeline.parse.figure_batch.release_model") as mock_release:
        stats = resolve_figures(files_elements, chroma_dir=chroma_dir, book_id=book_id)
    return stats, mock_desc, mock_release


def test_cache_hit_skips_describe_call(tmp_path):
    from pipeline.parse import vlm_cache
    import hashlib

    fig = _fig()  # metadata["image_bytes"] = b"png-bytes"
    sha = hashlib.sha256(b"png-bytes").hexdigest()
    vlm_cache.set(str(tmp_path), "b", sha, "cached description")

    with patch("pipeline.parse.figure_batch.OpenAI"), \
         patch("pipeline.parse.figure_batch.describe_image") as mock_desc, \
         patch("pipeline.parse.figure_batch.release_model"):
        stats = resolve_figures([[fig]], chroma_dir=str(tmp_path), book_id="b")

    mock_desc.assert_not_called()
    assert fig.content == "[alt: alt-text] cached description"
    assert fig.metadata["vlm_status"] == "described"
    assert stats.described == 1


def test_cache_miss_calls_describe_and_writes_cache(tmp_path):
    from pipeline.parse import vlm_cache
    import hashlib

    fig = _fig()
    sha = hashlib.sha256(b"png-bytes").hexdigest()

    stats, mock_desc, _ = _run_with_cache([[fig]], ["fresh description"],
                                          chroma_dir=str(tmp_path), book_id="b")

    mock_desc.assert_called_once()
    assert vlm_cache.get(str(tmp_path), "b", sha) == "fresh description"


def test_no_chroma_dir_skips_caching_entirely(tmp_path):
    """chroma_dir 不传时（现有调用方式）完全不碰缓存，行为跟改造前一致。"""
    fig = _fig()
    _run([[fig]], describe_side_effect=["desc"])  # 不传 chroma_dir/book_id
    assert fig.metadata["vlm_status"] == "described"


def test_internal_resize_call_removed():
    """阶段2 不再自己调 _resize_to_limit —— 缩放已经在阶段1 做过，
    连 import 都应该删掉（模块里不再有这个名字）。"""
    import pipeline.parse.figure_batch as fb
    assert not hasattr(fb, "_resize_to_limit")


def test_should_pause_stops_loop_without_marking_remaining_degraded():
    figs = [_fig(), _fig(), _fig()]
    calls = []

    def fake_should_pause():
        calls.append(1)
        return len(calls) > 1  # 第一张图处理完之后暂停

    with patch("pipeline.parse.figure_batch.OpenAI"), \
         patch("pipeline.parse.figure_batch.describe_image", return_value="d"), \
         patch("pipeline.parse.figure_batch.release_model"):
        stats = resolve_figures([figs], should_pause=fake_should_pause)

    assert stats.described == 1
    assert stats.degraded == 0  # 剩下两张没做完，但不算"降级"，也没被动过
    assert figs[1].metadata.get("vlm_status") is None
    assert figs[2].metadata.get("vlm_status") is None


# ── on_progress 回调 ─────────────────────────────────────────────────────

def test_on_progress_called_per_image_with_current_and_total():
    figs = [_fig(), _fig(), _fig()]
    updates = []

    with patch("pipeline.parse.figure_batch.OpenAI"), \
         patch("pipeline.parse.figure_batch.describe_image", return_value="d"), \
         patch("pipeline.parse.figure_batch.release_model"):
        resolve_figures([figs], on_progress=lambda c, t: updates.append((c, t)))

    assert updates == [(1, 3), (2, 3), (3, 3)]


def test_on_progress_still_called_for_degraded_images():
    figs = [_fig(), _fig()]
    updates = []

    with patch("pipeline.parse.figure_batch.OpenAI"), \
         patch("pipeline.parse.figure_batch.describe_image",
               side_effect=[ValueError("x"), "ok"]), \
         patch("pipeline.parse.figure_batch.release_model"):
        resolve_figures([figs], on_progress=lambda c, t: updates.append((c, t)))

    assert updates == [(1, 2), (2, 2)]


def test_no_on_progress_default_is_noop():
    fig = _fig()
    _run([[fig]], describe_side_effect=["desc"])  # 不传 on_progress，不应抛异常
