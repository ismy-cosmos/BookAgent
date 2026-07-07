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
         patch("pipeline.parse.figure_batch._release_model") as mock_release:
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
         patch("pipeline.parse.figure_batch._release_model") as mock_release:
        stats = resolve_figures([[Element(type="text", content="t", page_num=1)]])
    mock_cls.assert_not_called()
    mock_release.assert_not_called()
    assert stats == FigureBatchStats()


# ── per_image_tokens 记录（真实 usage.prompt_tokens 回传）───────────────────

def _fake_describe_with_usage(tokens):
    def _inner(client, model, b64, prompt=None, on_usage=None):
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
         patch("pipeline.parse.figure_batch._release_model"):
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
