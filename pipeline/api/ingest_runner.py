"""ImportQueue 的真正处理器：把计划1的 run_ingest 接进队列框架。

职责（都在工作线程里执行，不占 HTTP 请求线程）：
- 任务开始前，清理"用户提交时排除掉的文件"的缓存条目（spec 第4节触发点2）
- 把 run_ingest 的 ProgressUpdate 转成 dict 写进队列的共享进度状态
- 文件确定入库的瞬间把它从待导入列表移除（spec 第4节触发点1）
- 把 IngestResult 转成 summary dict 返回，由队列存档供进度接口查询
"""
from __future__ import annotations
import hashlib
from dataclasses import asdict
from typing import Callable

from pipeline.api import staging
from pipeline.api.config import get_chroma_dir
from pipeline.embed.embedder import release_gpu_model
from pipeline.parse import parse_cache, vlm_cache
from pipeline.store.chroma_store import get_store


def _purge_excluded_cache_entries(chroma_dir: str, book_id: str, keep_shas: set[str]) -> None:
    for sha in parse_cache.keys(chroma_dir, book_id):
        if sha in keep_shas:
            continue
        entry = parse_cache.get(chroma_dir, book_id, sha)
        if entry is not None:
            elements, _chunks = entry
            for elem in elements or []:
                img = elem.metadata.get("image_bytes")
                if elem.type == "figure" and img:
                    vlm_cache.delete(chroma_dir, book_id,
                                     hashlib.sha256(img).hexdigest())
        parse_cache.delete(chroma_dir, book_id, sha)


def ingest_processor(
    book_id: str,
    file_paths: list[str],
    should_pause: Callable[[], bool],
    report_progress: Callable[[dict], None],
) -> dict:
    from scripts.ingest import _sha256, run_ingest

    chroma_dir = get_chroma_dir()

    keep_shas: set[str] = set()
    for fp in file_paths:
        try:
            keep_shas.add(_sha256(fp))
        except OSError:
            pass  # 文件已不在磁盘上——阶段1会把它记为失败，这里只影响清理范围
    _purge_excluded_cache_entries(chroma_dir, book_id, keep_shas)

    def _on_committed(file_path: str) -> None:
        # 回调在 run_ingest 阶段3的 try 块内被调用（接口契约：不许抛异常）。
        # 列表更新失败只能吞掉——文件已真正入库，残留条目会在下次提交时
        # 走"已导入跳过"分支自愈。
        try:
            staging.remove_file(chroma_dir, book_id, file_path)
        except OSError as e:
            print(f"[warn] 待导入列表更新失败（文件已成功入库，下次提交时自愈）: {e}")

    try:
        result = run_ingest(
            book_id, file_paths, chroma_dir=chroma_dir,
            should_pause=should_pause,
            on_progress=lambda update: report_progress(asdict(update)),
            on_file_committed=_on_committed,
            store=get_store(chroma_dir),
        )
    finally:
        # 任务结束（成功/失败/暂停提前收尾都算）就释放 GPU embedder，不留到
        # 下一次导入才释放——避免跟 Ollama 抢显存，见 release_gpu_model 文档。
        release_gpu_model()
    return {
        "book_id": book_id,
        "total_chunks": result.total_chunks,
        "failures": result.failures,
        "not_attempted": result.not_attempted,
        "aborted_early": result.aborted_early,
    }
