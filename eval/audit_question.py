"""对 qa.jsonl 里的题目跑真实 answer() 管线，dump 回答 + 检索到的chunk全文，供人工审查。
用法: python eval/audit_question.py cs-b001 cs-b002 ...
依赖隔离评测库 book_id='cs-eval'（.chroma-eval-cs，见
docs/superpowers/plans/2026-07-20-cs-testset-audit-expansion.md Task 1）。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.agent.answer import answer
from pipeline.agent.client import OllamaAgentClient
from pipeline.agent.executor import RealExecutor
from pipeline.embed import Embedder
from pipeline.store import ChromaStore

_BOOK_ID = "cs-eval"
_CHROMA_DIR = str(Path(__file__).parent.parent / ".chroma-eval-cs")
_MODEL = "qwen3:q4km"
_QA_FILE = Path(__file__).parent / "testset/cs/qa/qa.jsonl"


class LoggingExecutor(RealExecutor):
    """RealExecutor 的审查专用子类：额外把模型自己组织的 retrieve query 打印出来。
    审查检索质量必须知道模型实际发了什么 query，不能拿题目原文代替——两者常常不同。"""

    def _retrieve(self, args: dict) -> str:
        print(f"\n  [retrieve调用] query={args.get('query', '')!r}  k={args.get('k', 5)}")
        return super()._retrieve(args)


def main() -> None:
    ids = sys.argv[1:]
    if not ids:
        print("用法: python eval/audit_question.py cs-b001 cs-b002 ...")
        sys.exit(1)

    qa_items = {}
    for line in open(_QA_FILE, encoding="utf-8"):
        if line.strip():
            item = json.loads(line)
            qa_items[item["id"]] = item

    store = ChromaStore(persist_dir=_CHROMA_DIR)
    embedder = Embedder(device="cpu")
    executor = LoggingExecutor(book_id=_BOOK_ID, embedder=embedder, store=store)
    client = OllamaAgentClient(model=_MODEL, executor=executor)

    for qid in ids:
        item = qa_items[qid]
        q = item["question"]
        print(f"\n{'=' * 100}\n[{qid}] ({item['question_type']}) {q}")
        print(f"标准答案: {item.get('standard_answer', '')!r}")
        print(f"source_location: {item.get('source_location', '')}")
        print(f"qa.jsonl里的supporting_chunks: {item.get('supporting_chunks', [])}")

        result = answer(q, history=[], client=client)
        print(f"\n--- 回答 ---\n{result.answer}")
        print(f"\n--- 引用的 {len(result.citations)} 个chunk ---")

        chunk_ids = list(dict.fromkeys(c.chunk_id for c in result.citations))
        full = {r["chunk_id"]: r for r in store.get(_BOOK_ID, chunk_ids)} if chunk_ids else {}
        for c in result.citations:
            r = full.get(c.chunk_id, {})
            print(f"\n  chunk_id={c.chunk_id}  source={c.source_file}  score={c.score}"
                  f"  page={r.get('page_start')}-{r.get('page_end')}")
            print(f"  content: {(r.get('content') or '')[:1200]}")


if __name__ == "__main__":
    main()
