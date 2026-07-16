"""VLM 批量描述内嵌图片。

位于 ingest 的解析阶段与分块入库阶段之间：收集整批所有带真实字节
（metadata["image_bytes"]）的 figure Element，逐张送本地 Ollama 视觉模型，
紧邻的 Figure/Table 说明行拼入 prompt 作上下文，描述写回 Element.content。
模型整批只加载一次、处理完全部图片后释放一次（keep_alive=0）。

失败语义：单张失败只降级该图（content 保持占位符原样）；连续失败达阈值
（VLM_MAX_CONSECUTIVE_FAILURES，默认 3，跨整批计数、成功即清零）判定
Ollama 系统性不可用，剩余图片直接降级不再等待超时。
"""
from __future__ import annotations
import base64
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Callable

import httpx
from openai import OpenAI, OpenAIError

from pipeline.parse import vlm_cache
from pipeline.parse.base import CAPTION_RE, Element
from pipeline.parse.image import (
    _DESCRIBE_PROMPT,
    _OLLAMA_BASE,
    _VLM_MODEL,
    _release_model,
    describe_image,
)

_DEFAULT_MAX_CONSECUTIVE_FAILURES = 3
_ALT_RE = re.compile(r"^!\[([^\]]*)\]")


@dataclass
class FigureBatchStats:
    described: int = 0
    degraded: int = 0
    no_bytes: int = 0            # figure 元素但没有 image_bytes（获取失败，静默维持现状）
    breaker_tripped: bool = False
    elapsed_s: float = 0.0       # VLM 批量阶段总耗时（不含模型释放，wall-clock 秒）
    per_image_s: list[float] = field(default_factory=list)  # 每张图 VLM 调用耗时
    per_image_tokens: list[int] = field(default_factory=list)  # 每张图 prompt_tokens（视觉+文本），失败/无usage的图不计入


def _caption_for(elements: list[Element], idx: int) -> str:
    if idx + 1 < len(elements):
        nxt = elements[idx + 1]
        if nxt.type == "text" and CAPTION_RE.match(nxt.content):
            return nxt.content
    return ""


def _build_prompt(caption: str) -> str:
    if not caption:
        return _DESCRIBE_PROMPT
    return (
        f'This figure is captioned in the source text as: "{caption}". '
        f"Use the caption as context. {_DESCRIBE_PROMPT}"
    )


def _mark_degraded(elem: Element, stats: FigureBatchStats) -> None:
    elem.metadata["vlm_status"] = "degraded"
    elem.metadata.pop("image_bytes", None)
    stats.degraded += 1


def resolve_figures(
    files_elements: list[list[Element]],
    model: str = _VLM_MODEL,
    ollama_base: str = _OLLAMA_BASE,
    timeout: float = 120.0,
    chroma_dir: str | None = None,
    book_id: str | None = None,
    should_pause: Callable[[], bool] = lambda: False,
    on_progress: Callable[[int, int], None] = lambda current, total: None,
) -> FigureBatchStats:
    stats = FigureBatchStats()
    targets: list[tuple[Element, str]] = []
    for elements in files_elements:
        for i, elem in enumerate(elements):
            if elem.type != "figure":
                continue
            if elem.metadata.get("image_bytes"):
                targets.append((elem, _caption_for(elements, i)))
            else:
                stats.no_bytes += 1

    if not targets:
        return stats

    max_fail = int(os.environ.get(
        "VLM_MAX_CONSECUTIVE_FAILURES", str(_DEFAULT_MAX_CONSECUTIVE_FAILURES)))
    base = ollama_base.rstrip("/")
    client = OpenAI(
        base_url=f"{base}/v1", api_key="ollama",
        http_client=httpx.Client(trust_env=False), timeout=timeout,
    )
    consecutive = 0
    t_start = time.perf_counter()
    try:
        for n, (elem, caption) in enumerate(targets, start=1):
            on_progress(n, len(targets))
            if should_pause():
                print(f"\n  [pause] 收到暂停请求，VLM 批量描述在第 {n}/{len(targets)} 张图边界停止。")
                break
            if stats.breaker_tripped:
                _mark_degraded(elem, stats)
                continue
            image_bytes = elem.metadata["image_bytes"]
            image_sha = hashlib.sha256(image_bytes).hexdigest()
            cached_desc = vlm_cache.get(chroma_dir, book_id, image_sha) if chroma_dir else None
            if cached_desc is not None:
                alt_m = _ALT_RE.match(elem.content)
                alt = alt_m.group(1).strip() if alt_m else ""
                elem.content = f"[alt: {alt}] {cached_desc}" if alt else cached_desc
                elem.metadata["vlm_status"] = "described"
                elem.metadata.pop("image_bytes", None)
                stats.described += 1
                consecutive = 0
                print(f"  VLM 描述 {n}/{len(targets)}（缓存命中）", end="\r")
                continue
            b64 = base64.b64encode(image_bytes).decode()
            t_img = time.perf_counter()
            usage_holder: list = []
            try:
                desc = describe_image(
                    client, model, b64, prompt=_build_prompt(caption),
                    options={"temperature": 0},
                    on_usage=lambda u: usage_holder.append(u.prompt_tokens),
                )
            except (OpenAIError, ValueError) as e:
                dt = time.perf_counter() - t_img
                stats.per_image_s.append(dt)
                print(f"  [warn] 第 {n}/{len(targets)} 张图 VLM 描述失败（{dt:.1f}s），已降级为占位符: {e}")
                _mark_degraded(elem, stats)
                consecutive += 1
                if max_fail and consecutive >= max_fail:
                    stats.breaker_tripped = True
                    print(f"  [warn] 连续 {consecutive} 张图 VLM 调用失败，"
                          f"疑似 Ollama 不可用，剩余 {len(targets) - n} 张图全部降级。")
                continue
            dt = time.perf_counter() - t_img
            stats.per_image_s.append(dt)
            if usage_holder:
                stats.per_image_tokens.append(usage_holder[0])
            alt_m = _ALT_RE.match(elem.content)
            alt = alt_m.group(1).strip() if alt_m else ""
            elem.content = f"[alt: {alt}] {desc}" if alt else desc
            elem.metadata["vlm_status"] = "described"
            elem.metadata.pop("image_bytes", None)
            stats.described += 1
            consecutive = 0
            if chroma_dir:
                vlm_cache.set(chroma_dir, book_id, image_sha, desc)
            tok_str = f", {usage_holder[0]} tok" if usage_holder else ""
            print(f"  VLM 描述 {n}/{len(targets)} 完成 ({dt:.1f}s{tok_str})", end="\r")
    finally:
        stats.elapsed_s = time.perf_counter() - t_start
        tok_summary = ""
        if stats.per_image_tokens:
            total_tok = sum(stats.per_image_tokens)
            avg_tok = total_tok / len(stats.per_image_tokens)
            tok_summary = f"，token 总计 {total_tok}（avg {avg_tok:.0f}/图）"
        print(f"\n  VLM 批量阶段总耗时 {stats.elapsed_s:.1f}s，"
              f"共 {len(targets)} 张图"
              + (f"，avg {stats.elapsed_s/len(targets):.1f}s/图"
                 if targets else "")
              + tok_summary)
        _release_model(base, model)
    return stats
