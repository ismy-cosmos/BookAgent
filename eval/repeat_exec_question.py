"""Repeat the exec()-question 5x to check whether MAX_ROUNDS_EXCEEDED is a
one-off sampling fluke (temperature=1 in the deployed Modelfile) or a
reproducible failure mode.

Usage: python eval/repeat_exec_question.py
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.agent.answer import answer
from pipeline.agent.client import OllamaAgentClient
from pipeline.agent.executor import RealExecutor
from pipeline.embed import Embedder
from pipeline.store import ChromaStore

_BOOK_ID = "cs-eval-60"
_CHROMA_DIR = ".chroma-eval-cs60"
_MODEL = "qwen3:q4km"
_Q = "exec() 系列调用成功执行后为什么不会返回到调用它的代码？"
_N_RUNS = 5


def main() -> None:
    store = ChromaStore(persist_dir=_CHROMA_DIR)
    embedder = Embedder(device="cpu")
    executor = RealExecutor(book_id=_BOOK_ID, embedder=embedder, store=store)
    client = OllamaAgentClient(model=_MODEL, executor=executor)

    exceeded = 0
    for i in range(1, _N_RUNS + 1):
        result = answer(_Q, history=[], client=client)
        is_exceeded = "[MAX_ROUNDS_EXCEEDED]" in result.answer
        exceeded += is_exceeded
        print(f"[run {i}/{_N_RUNS}] {'MAX_ROUNDS_EXCEEDED' if is_exceeded else 'OK'} "
              f"tokens={result.total_tokens} latency={result.latency_s:.1f}s "
              f"tool={result.triggered_tool}")
        if not is_exceeded:
            print(f"  答案前120字: {result.answer[:120]}")

    print(f"\n复现率: {exceeded}/{_N_RUNS}")


if __name__ == "__main__":
    main()
