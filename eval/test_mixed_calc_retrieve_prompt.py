"""Verify issue #17 的"计算 + 书本知识混合型问题"prompt修复：模型该不该同一轮里
既 retrieve 又 calculate。用两个不同措辞、不同场景的复合题各跑几次，检查
attempted_retrieve/used_calculate 是否稳定为 True。

Usage: python eval/test_mixed_calc_retrieve_prompt.py
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.agent.client import OllamaAgentClient
from pipeline.agent.executor import RealExecutor
from pipeline.chunk.schema import Chunk
from pipeline.store import ChromaStore

_MODEL = "qwen3:q4km"
_CHROMA_ROOT = Path("/tmp/bookagent-eval-mixed-calc-retrieve")
_RUNS_PER_CASE = 3


class _FakeEmbedder:
    """检索排序不是这次要验证的东西，固定向量即可——只关心 attempted_retrieve/used_calculate。"""
    def embed_query(self, text: str) -> list:
        return [0.1] * 1024


_CASES = [
    {
        "label": "FIFO周转时间",
        "chunk_content": "FIFO调度：按到达顺序依次运行，周转时间=完成时间-到达时间。",
        "question": "三个任务A(5ms)、B(10ms)、C(15ms)同时在t=0到达，"
                    "FIFO按A→B→C顺序调度，平均周转时间是多少？",
    },
    {
        "label": "Round-Robin时间片",
        "chunk_content": "Round-Robin(RR)调度：每个任务运行一个时间片(time slice)后被抢占，"
                          "轮到下一个任务，循环执行直到所有任务完成。",
        "question": "一个线程池用round-robin方式调度，每个任务的时间片是3ms，"
                    "如果有5个任务在队列里等待，处理完全部5个任务最少需要多长时间？",
    },
]


_dir_counter = 0


def _run_case(case: dict) -> None:
    global _dir_counter
    print(f"── {case['label']} ──")
    hits_retrieve = hits_calculate = 0
    for i in range(_RUNS_PER_CASE):
        # chromadb 的 rust binding 内部按绝对路径缓存连接，同一个 process 里
        # 复用同一个目录路径（哪怕中间 rmtree 过）会撞见 "readonly database"，
        # 每次跑都换一个全新路径规避，不是 rmtree 时机的问题。
        _dir_counter += 1
        chroma_dir = _CHROMA_ROOT / f"run-{_dir_counter}"
        store = ChromaStore(persist_dir=str(chroma_dir))
        chunk = Chunk(
            chunk_id="b/f/p0001/0000", book_id="eval-book", source_file="f.pdf",
            element_type="text", content=case["chunk_content"], token_count=20,
            page_start=1, page_end=1,
        )
        store.add_chunks("eval-book", [chunk], [[0.1] * 1024])
        executor = RealExecutor(book_id="eval-book", embedder=_FakeEmbedder(), store=store)
        client = OllamaAgentClient(model=_MODEL, executor=executor)
        turn = client.run(case["question"])
        hits_retrieve += turn.attempted_retrieve
        hits_calculate += turn.used_calculate
        print(f"  run {i+1}: attempted_retrieve={turn.attempted_retrieve}  "
              f"used_calculate={turn.used_calculate}  "
              f"final_answer={turn.final_answer[:60]!r}")
    print(f"  汇总: retrieve {hits_retrieve}/{_RUNS_PER_CASE}  calculate {hits_calculate}/{_RUNS_PER_CASE}")
    print()


def main():
    for case in _CASES:
        _run_case(case)
    shutil.rmtree(_CHROMA_ROOT, ignore_errors=True)


if __name__ == "__main__":
    main()
