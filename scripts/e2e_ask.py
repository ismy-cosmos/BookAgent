"""Real end-to-end retrieval + multi-turn agent smoke test (human-reviewed, no assertions).

Prerequisites:
    1. Ollama running locally with `qwen3:q4km` pulled (used for both agent reasoning
       and VLM image captioning during ingest).
    2. Real data ingested into the `java-ch1-e2e` book:
        python scripts/ingest.py --book-id java-ch1-e2e \
            --file eval/testset/cs/raw/book/java-ch1-e2e.epub \
            --dir eval/testset/cs/raw/pic/

Usage:
    python scripts/e2e_ask.py
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

_BOOK_ID = "java-ch1-e2e"
_MODEL = "qwen3:q4km"

_QUESTIONS = [
    "这一章主要讲了 Java 的哪些内容？",
    "书中提到的 RAG 相关流程图讲了什么？",
    "刚才那张 RAG 流程图具体提到了哪些挑战？",  # 追问：验证多轮 + get_chunk 按句柄水化
    "书里提到基孔肯雅热了吗？如果提到了，说了什么？",
    "地球到月球的距离是多少？",  # 书中无据，验证「未找到参考资料」
]


def main() -> None:
    store = ChromaStore()
    count = store.count(_BOOK_ID)
    if count == 0:
        print(f"[错误] book_id '{_BOOK_ID}' 在 chroma 中没有数据，请先运行 ingest（见文件头 Prerequisites）。")
        sys.exit(1)
    print(f"book '{_BOOK_ID}' 共 {count} 个 chunk，开始多轮问答...\n")

    embedder = Embedder()
    executor = RealExecutor(book_id=_BOOK_ID, embedder=embedder, store=store)
    client = OllamaAgentClient(model=_MODEL, executor=executor)

    history: list = []
    for i, question in enumerate(_QUESTIONS, start=1):
        print(f"--- 第 {i} 轮 ---")
        print(f"Q: {question}")
        result = answer(question, history=history, client=client)
        print(f"A: {result.answer}")
        print(f"触发工具: {result.triggered_tool}  tokens: {result.total_tokens}  延迟: {result.latency_s:.1f}s")
        if result.citations:
            print("引用:")
            for c in result.citations:
                print(f"  - [{c.element_type}] {c.citation}  (chunk_id={c.chunk_id}, score={c.score})")
        print()
        history = result.history


if __name__ == "__main__":
    main()